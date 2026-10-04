"""Pravidla a operace s lety: kdo smí co, pravidla posádky podle účelu, založení letu,
vzlet, přistání a zrušení. API (lety/api.py) jen převádí data a volá tyto funkce."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from osoby.models import Kategorie, Osoba

from . import audit
from .models import (
    AuditLog,
    DuvodOpravy,
    DuvodZruseni,
    FunkcePosadky,
    KratkyLet,
    Let,
    Letadlo,
    Letiste,
    Posadka,
    StavLetu,
    Ucel,
    Uloha,
    ZpusobVzletu,
)

KRATKY_LET = timedelta(seconds=60)


class ChybaLetu(Exception):
    """Chyba, kterou má uživatel vidět. `kod` pomáhá frontendu (např. nabídnout dialog)."""

    def __init__(self, zprava: str, status: int = 400, kod: str = "", let_id: int | None = None):
        super().__init__(zprava)
        self.zprava = zprava
        self.status = status
        self.kod = kod
        self.let_id = let_id


# --- kdo smí co --------------------------------------------------------------


def ridi_provoz(osoba: Osoba) -> bool:
    """Časoměřič/věž a admin řídí provoz – ovládají lety všech.

    Účetní do běžícího provozu nezasahuje (jako pilot ovládá jen své lety); jeho práva
    navíc se týkají až oprav ukončených letů po uzávěrce (etapa oprav a uzávěrek).
    """
    return osoba.is_staff or osoba.role_casomeric


def je_vlastnik(osoba: Osoba, let: Let) -> bool:
    """„Vlastní let“ = založil ho, nebo je na něm PIC, žák či přezkoušený."""
    if let.zalozil_id == osoba.pk:
        return True
    return any(
        p.osoba_id == osoba.pk
        and p.funkce in (FunkcePosadky.PIC, FunkcePosadky.ZAK, FunkcePosadky.PREZKOUSENY)
        for p in let.posadka.all()
    )


def muze_ovladat(osoba: Osoba, let: Let) -> bool:
    return ridi_provoz(osoba) or je_vlastnik(osoba, let)


def over_pravo(osoba: Osoba, let: Let) -> None:
    if not muze_ovladat(osoba, let):
        raise ChybaLetu("Tento let může ovládat jen jeho posádka nebo časoměřič.", status=403)


# --- pravidla posádky ----------------------------------------------------------

# Účel → (povinné funkce kromě PIC, dovolené funkce kromě PIC)
PRAVIDLA_POSADKY = {
    Ucel.NORMALNI: (set(), {FunkcePosadky.CLEN}),
    Ucel.VYCVIK: ({FunkcePosadky.ZAK}, {FunkcePosadky.ZAK}),
    Ucel.VYCVIK_SOLO: ({FunkcePosadky.DOZOR}, {FunkcePosadky.DOZOR}),
    Ucel.PREZKOUSENI: ({FunkcePosadky.PREZKOUSENY}, {FunkcePosadky.PREZKOUSENY}),
    Ucel.VLEK: (set(), set()),  # jen vlekař (PIC)
}

NAZEV_FUNKCE = dict(FunkcePosadky.choices)


@dataclass
class ClenPosadky:
    osoba_id: int
    funkce: str


@dataclass
class NovyLet:
    letadlo_id: int
    ucel: str
    posadka: list[ClenPosadky]
    uloha_id: int | None = None
    zpusob_vzletu: str = ZpusobVzletu.VLASTNI
    misto_vzletu_id: int | None = None
    pocet_hostu: int = 0
    platce_id: int | None = None
    plati_aeroklub: bool = False
    # akce: "pripravit" | "vzlet" (teď nebo v čase cas_vzletu) | "dopsat" (proběhlý let)
    akce: str = "vzlet"
    cas_vzletu: datetime | None = None
    cas_pristani: datetime | None = None
    misto_pristani_id: int | None = None
    pocet_tg: int = 0
    kratky_let: str = ""
    # U kluzáku ve vleku: {"letadlo_id", "vlekar_id", "cas_pristani" (jen u dopsaného letu)}
    vlek: dict | None = None
    osoby: dict[int, Osoba] = field(default_factory=dict)


def _over_posadku(data: NovyLet, letadlo: Letadlo) -> None:
    if data.ucel not in PRAVIDLA_POSADKY:
        raise ChybaLetu("Neznámý účel letu.")
    povinne, dovolene = PRAVIDLA_POSADKY[data.ucel]

    funkce = [c.funkce for c in data.posadka]
    if funkce.count(FunkcePosadky.PIC) != 1:
        raise ChybaLetu("Let musí mít právě jednoho PIC.")
    ostatni = [f for f in funkce if f != FunkcePosadky.PIC]
    for f in ostatni:
        if f not in dovolene:
            raise ChybaLetu(f"U tohoto účelu letu nemůže být „{NAZEV_FUNKCE.get(f, f)}“.")
    for f in povinne:
        if f not in ostatni:
            raise ChybaLetu(f"U tohoto účelu letu chybí „{NAZEV_FUNKCE[f]}“.")
    if len(ostatni) != len(set(ostatni)) and data.ucel != Ucel.NORMALNI:
        raise ChybaLetu("Každá funkce může být na letu jen jednou.")

    ids = [c.osoba_id for c in data.posadka]
    if len(ids) != len(set(ids)):
        raise ChybaLetu("Stejná osoba je v posádce vícekrát.")
    osoby = {o.pk: o for o in Osoba.objects.filter(pk__in=ids, is_active=True)}
    if len(osoby) != len(ids):
        raise ChybaLetu("Některá osoba v posádce neexistuje nebo není aktivní.")
    for c in data.posadka:
        if osoby[c.osoba_id].externi and not (
            c.funkce == FunkcePosadky.PIC and data.ucel == Ucel.PREZKOUSENI
        ):
            raise ChybaLetu("Externí osoba může být jen PIC při přezkoušení.")
    data.osoby = osoby

    na_palube = sum(1 for f in funkce if f != FunkcePosadky.DOZOR) + data.pocet_hostu
    if na_palube > letadlo.pocet_mist:
        raise ChybaLetu(
            f"{letadlo.imatrikulace} má {letadlo.pocet_mist} míst, na palubě by bylo {na_palube}."
        )


def vychozi_platce(data: NovyLet) -> int | None:
    """Kdo let platí: výcvik žák, přezkoušení přezkoušený, jinak PIC."""
    hledana = {
        Ucel.VYCVIK: FunkcePosadky.ZAK,
        Ucel.VYCVIK_SOLO: FunkcePosadky.PIC,  # při sólu je PIC žák
        Ucel.PREZKOUSENI: FunkcePosadky.PREZKOUSENY,
    }.get(data.ucel, FunkcePosadky.PIC)
    return next((c.osoba_id for c in data.posadka if c.funkce == hledana), None)


def _over_platce(data: NovyLet) -> None:
    if data.plati_aeroklub:
        data.platce_id = None
        return
    if data.platce_id is None:
        data.platce_id = vychozi_platce(data)
    if data.platce_id not in data.osoby:
        raise ChybaLetu("Plátce musí být člen posádky, nebo aeroklub.")
    if data.osoby[data.platce_id].externi:
        raise ChybaLetu("Externí osoba nemůže let platit.")


def _over_ulohu(data: NovyLet, letadlo: Letadlo) -> Uloha | None:
    if data.uloha_id is None:
        return None
    uloha = Uloha.objects.select_related("osnova").filter(pk=data.uloha_id, aktivni=True).first()
    if uloha is None:
        raise ChybaLetu("Úloha neexistuje nebo není aktivní.")
    if uloha.osnova.kategorie != letadlo.kategorie:
        raise ChybaLetu("Úloha nepatří ke kategorii tohoto letadla.")
    if data.ucel not in uloha.ucely:
        raise ChybaLetu("Úloha se k tomuto účelu letu nehodí.")
    return uloha


def _over_zpusob_vzletu(data: NovyLet, letadlo: Letadlo) -> None:
    if letadlo.kategorie == Kategorie.KLUZAK:
        if data.zpusob_vzletu not in (
            ZpusobVzletu.NAVIJAK,
            ZpusobVzletu.AUTOSTART,
            ZpusobVzletu.VLEK,
        ):
            raise ChybaLetu("U kluzáku vyberte způsob vzletu.")
    else:
        data.zpusob_vzletu = ZpusobVzletu.VLASTNI


def _domovske_letiste() -> Letiste:
    letiste = Letiste.objects.filter(domovske=True).first()
    if letiste is None:
        raise ChybaLetu("Není nastavené domovské letiště.")
    return letiste


def _letiste(letiste_id: int | None) -> Letiste:
    if letiste_id is None:
        return _domovske_letiste()
    letiste = Letiste.objects.filter(pk=letiste_id, aktivni=True).first()
    if letiste is None:
        raise ChybaLetu("Letiště neexistuje nebo není aktivní.")
    return letiste


def _over_cas(cas: datetime, nazev: str) -> datetime:
    ted = timezone.now()
    if cas > ted + timedelta(minutes=1):
        raise ChybaLetu(f"{nazev} nemůže být v budoucnosti.")
    if cas < ted - timedelta(days=31):
        raise ChybaLetu(f"{nazev} je víc než měsíc zpátky.")
    return cas.replace(microsecond=0)


def _over_volne_osoby(osoby_ids, od: datetime, do: datetime | None, vyjma: int | None) -> None:
    """Jedna osoba nemůže letět dvěma lety zároveň (dozor na zemi se nepočítá).

    Řádky osob se zamknou, takže dva současné vzlety téže osoby projdou postupně.
    """
    ids = list(osoby_ids)
    list(Osoba.objects.select_for_update().filter(pk__in=ids).values_list("pk", flat=True))
    obsazeno = (
        Posadka.objects.select_related("osoba", "let__letadlo")
        .filter(osoba_id__in=ids, let__cas_vzletu__isnull=False)
        .exclude(funkce=FunkcePosadky.DOZOR)
        .exclude(let__stav=StavLetu.ZRUSEN)
        .exclude(let_id=vyjma)
        .filter(Q(let__cas_pristani__isnull=True) | Q(let__cas_pristani__gt=od))
    )
    if do is not None:
        obsazeno = obsazeno.filter(let__cas_vzletu__lt=do)
    clen = obsazeno.order_by("let__cas_vzletu").first()
    if clen is None:
        return
    jiny = clen.let
    kdy = "je právě ve vzduchu" if jiny.cas_pristani is None else "v tu dobu letí"
    raise ChybaLetu(
        f"{clen.osoba.get_full_name()} {kdy} na {jiny.letadlo.imatrikulace} "
        f"(vzlet {jiny.cas_vzletu:%H:%M} UTC).",
        status=409,
        kod="osoba_obsazena",
        let_id=jiny.pk,
    )


def _letici(posadka) -> list[int]:
    return [c.osoba_id for c in posadka if c.funkce != FunkcePosadky.DOZOR]


def _uloz(let: Let) -> None:
    """Uloží let; pojistku „letadlo bez překryvu“ převede na srozumitelnou zprávu."""
    try:
        with transaction.atomic():
            let.save()
    except IntegrityError as e:
        if "letadlo_bez_prekryvu" not in str(e):
            raise
        jiny = (
            Let.objects.filter(letadlo_id=let.letadlo_id, cas_vzletu__isnull=False)
            .exclude(stav=StavLetu.ZRUSEN)
            .exclude(pk=let.pk)
            .filter(Q(cas_pristani__isnull=True) | Q(cas_pristani__gt=let.cas_vzletu))
            .order_by("-cas_vzletu")
            .first()
        )
        raise ChybaLetu(
            f"{let.letadlo.imatrikulace} už má v tomto čase jiný let"
            + (f" (vzlet {jiny.cas_vzletu:%H:%M} UTC)." if jiny else "."),
            status=409,
            kod="letadlo_obsazeno",
            let_id=jiny.pk if jiny else None,
        ) from e


def partner(let: Let) -> Let | None:
    """Druhý let z dvojice kluzák + vlek (nebo None)."""
    if let.vlecny_let_id:
        return let.vlecny_let
    return Let.objects.filter(vlecny_let=let).first()


def _over_vlek(data: NovyLet, letadlo: Letadlo) -> tuple[Letadlo, Osoba] | None:
    """U kluzáku ve vleku ověří vlečné letadlo a vlekaře."""
    if data.zpusob_vzletu != ZpusobVzletu.VLEK or letadlo.kategorie != Kategorie.KLUZAK:
        if data.vlek:
            raise ChybaLetu("Vlečné letadlo se zadává jen u kluzáku ve vleku.")
        return None
    if not data.vlek or not data.vlek.get("letadlo_id") or not data.vlek.get("vlekar_id"):
        raise ChybaLetu("U vleku vyberte vlečné letadlo a vlekaře.")
    vlecne = Letadlo.objects.filter(pk=data.vlek["letadlo_id"], aktivni=True, vlecne=True).first()
    if vlecne is None:
        raise ChybaLetu("Vlečné letadlo neexistuje, není aktivní nebo nemůže vlekat.")
    vlekar = Osoba.objects.filter(pk=data.vlek["vlekar_id"], is_active=True, externi=False).first()
    if vlekar is None:
        raise ChybaLetu("Vlekař neexistuje nebo není aktivní.")
    if vlekar.pk in {c.osoba_id for c in data.posadka}:
        raise ChybaLetu("Vlekař nemůže být zároveň v posádce kluzáku.")
    return vlecne, vlekar


@transaction.atomic
def zalozit(data: NovyLet, kdo: Osoba) -> Let:
    letadlo = Letadlo.objects.filter(pk=data.letadlo_id, aktivni=True).first()
    if letadlo is None:
        raise ChybaLetu("Letadlo neexistuje nebo není aktivní.")
    if data.ucel == Ucel.VLEK:
        raise ChybaLetu("Vlek se zakládá u kluzáku volbou způsobu vzletu „Vlek“.")
    if data.pocet_hostu < 0 or data.pocet_tg < 0:
        raise ChybaLetu("Počty nemohou být záporné.")
    _over_posadku(data, letadlo)
    _over_platce(data)
    uloha = _over_ulohu(data, letadlo)
    _over_zpusob_vzletu(data, letadlo)
    vlek = _over_vlek(data, letadlo)

    let = Let(
        letadlo=letadlo,
        ucel=data.ucel,
        uloha=uloha,
        zpusob_vzletu=data.zpusob_vzletu,
        misto_vzletu=_letiste(data.misto_vzletu_id),
        pocet_hostu=data.pocet_hostu,
        platce_id=data.platce_id,
        plati_aeroklub=data.plati_aeroklub,
        soukrome=letadlo.soukrome,
        zalozil=kdo,
    )
    if data.akce == "pripravit":
        let.stav = StavLetu.PRIPRAVEN
    elif data.akce == "vzlet":
        let.stav = StavLetu.VE_VZDUCHU
        let.cas_vzletu = _over_cas(data.cas_vzletu or timezone.now(), "Vzlet")
    elif data.akce == "dopsat":
        if not data.cas_vzletu or not data.cas_pristani:
            raise ChybaLetu("U dopsaného letu zadejte vzlet i přistání.")
        let.cas_vzletu = _over_cas(data.cas_vzletu, "Vzlet")
        let.cas_pristani = _over_cas(data.cas_pristani, "Přistání")
        if let.cas_pristani < let.cas_vzletu:
            raise ChybaLetu("Přistání nemůže být dřív než vzlet.")
        let.stav = StavLetu.UKONCEN
        let.misto_pristani = _letiste(data.misto_pristani_id)
        let.pocet_tg = data.pocet_tg
        let.kratky_let = _kratky_let(let, data.kratky_let)
    else:
        raise ChybaLetu("Neznámá akce.")

    if let.cas_vzletu:
        _over_volne_osoby(_letici(data.posadka), let.cas_vzletu, let.cas_pristani, None)
    if vlek:
        let.vlecny_let = _zalozit_vlek(let, data, vlek, kdo)
    _uloz(let)
    let.posadka.bulk_create(
        [let.posadka.model(let=let, osoba_id=c.osoba_id, funkce=c.funkce) for c in data.posadka]
    )
    audit.zapsat(
        kdo,
        "zalozeni",
        "let",
        let.pk,
        zmeny={
            "akce": data.akce,
            "letadlo": letadlo.imatrikulace,
            "ucel": data.ucel,
            "posadka": [[c.osoba_id, c.funkce] for c in data.posadka],
            "cas_vzletu": let.cas_vzletu.isoformat() if let.cas_vzletu else None,
            "cas_pristani": let.cas_pristani.isoformat() if let.cas_pristani else None,
        },
    )
    return let


def _zalozit_vlek(kluzak: Let, data: NovyLet, vlek: tuple[Letadlo, Osoba], kdo: Osoba) -> Let:
    """Let vlečného letadla: stejný vzlet jako kluzák, platí ho plátce kluzáku."""
    vlecne, vlekar = vlek
    tah = Let(
        letadlo=vlecne,
        ucel=Ucel.VLEK,
        zpusob_vzletu=ZpusobVzletu.VLASTNI,
        misto_vzletu=kluzak.misto_vzletu,
        platce_id=kluzak.platce_id,
        plati_aeroklub=kluzak.plati_aeroklub,
        soukrome=vlecne.soukrome,
        zalozil=kdo,
        stav=kluzak.stav,
        cas_vzletu=kluzak.cas_vzletu,
    )
    if kluzak.stav == StavLetu.UKONCEN:  # dopsaný let – vlečná má vlastní přistání
        cas = data.vlek.get("cas_pristani")
        if not cas:
            raise ChybaLetu("U dopsaného vleku zadejte i přistání vlečného letadla.")
        tah.cas_pristani = _over_cas(_datum(cas), "Přistání vlečné")
        if tah.cas_pristani < tah.cas_vzletu:
            raise ChybaLetu("Přistání vlečné nemůže být dřív než vzlet.")
        tah.misto_pristani = kluzak.misto_vzletu
        tah.kratky_let = _kratky_let(tah, KratkyLet.NORMALNI)
    if tah.cas_vzletu:
        _over_volne_osoby([vlekar.pk], tah.cas_vzletu, tah.cas_pristani, None)
    _uloz(tah)
    tah.posadka.create(osoba=vlekar, funkce=FunkcePosadky.PIC)
    audit.zapsat(
        kdo,
        "zalozeni",
        "let",
        tah.pk,
        zmeny={"vlek pro": kluzak.letadlo.imatrikulace, "vlekař": vlekar.get_full_name()},
    )
    return tah


def _datum(hodnota) -> datetime:
    return hodnota if isinstance(hodnota, datetime) else datetime.fromisoformat(str(hodnota))


def _zamknout(let_id: int) -> Let:
    """Načte let se zámkem řádku – dva současné stisky se tak zpracují postupně."""
    let = (
        Let.objects.select_for_update()
        .select_related("letadlo")
        .prefetch_related("posadka")
        .filter(pk=let_id)
        .first()
    )
    if let is None:
        raise ChybaLetu("Let neexistuje.", status=404)
    return let


def _kdo_naposledy(let: Let, *akce: str) -> str:
    zaznam = (
        AuditLog.objects.select_related("kdo")
        .filter(objekt="let", objekt_id=let.pk, akce__in=akce)
        .order_by("-kdy")
        .first()
    )
    return f" ({zaznam.kdo.get_full_name()})" if zaznam and zaznam.kdo else ""


@transaction.atomic
def vzlet(let_id: int, kdo: Osoba, cas: datetime | None = None) -> Let:
    let = _zamknout(let_id)
    over_pravo(kdo, let)
    if let.stav == StavLetu.ZRUSEN:
        raise ChybaLetu("Let je zrušený.", status=409)
    if let.stav != StavLetu.PRIPRAVEN:
        raise ChybaLetu(
            f"Vzlet už je zapsaný v {let.cas_vzletu:%H:%M:%S} UTC"
            f"{_kdo_naposledy(let, 'vzlet', 'zalozeni', 'oprava')}.",
            status=409,
            kod="uz_zapsano",
            let_id=let.pk,
        )
    cas_vzletu = _over_cas(cas or timezone.now(), "Vzlet")
    dvojice = [let]
    druhy = partner(let)
    if druhy is not None:  # kluzák a vlečná startují spolu
        druhy = _zamknout(druhy.pk)
        if druhy.stav != StavLetu.PRIPRAVEN:
            raise ChybaLetu(f"{druhy.letadlo.imatrikulace} z dvojice vleku už není připravený.")
        dvojice.append(druhy)
    for jeden in dvojice:
        jeden.cas_vzletu = cas_vzletu
        _over_volne_osoby(_letici(jeden.posadka.all()), cas_vzletu, None, jeden.pk)
        jeden.stav = StavLetu.VE_VZDUCHU
        jeden.verze += 1
        _uloz(jeden)
        audit.zapsat(kdo, "vzlet", "let", jeden.pk, zmeny={"cas_vzletu": cas_vzletu.isoformat()})
    return let


def _kratky_let(let: Let, volba: str) -> str:
    """U letu do 1 minuty musí uživatel říct, jak ho brát (kap. 3.5 návrhu)."""
    if let.cas_pristani - let.cas_vzletu >= KRATKY_LET:
        return ""
    if volba not in KratkyLet.values:
        raise ChybaLetu(
            "Let trval méně než minutu. Jak ho brát?", status=409, kod="kratky_let", let_id=let.pk
        )
    return volba


@transaction.atomic
def pristani(
    let_id: int,
    kdo: Osoba,
    cas: datetime | None = None,
    misto_pristani_id: int | None = None,
    pocet_tg: int = 0,
    kratky_let: str = "",
) -> Let:
    let = _zamknout(let_id)
    over_pravo(kdo, let)
    if let.stav == StavLetu.PRIPRAVEN:
        raise ChybaLetu("Let ještě nevzlétl.", status=409)
    if let.stav != StavLetu.VE_VZDUCHU:
        konec = f" v {let.cas_pristani:%H:%M:%S} UTC" if let.cas_pristani else ""
        raise ChybaLetu(
            f"Přistání už je zapsané{konec}"
            f"{_kdo_naposledy(let, 'pristani', 'zalozeni', 'oprava')}.",
            status=409,
            kod="uz_zapsano",
            let_id=let.pk,
        )
    if pocet_tg < 0:
        raise ChybaLetu("Počet touch-and-go nemůže být záporný.")
    let.cas_pristani = _over_cas(cas or timezone.now(), "Přistání")
    if let.cas_pristani < let.cas_vzletu:
        raise ChybaLetu("Přistání nemůže být dřív než vzlet.")
    let.kratky_let = _kratky_let(let, kratky_let)
    let.misto_pristani = _letiste(misto_pristani_id)
    let.pocet_tg = pocet_tg
    let.stav = StavLetu.UKONCEN
    let.verze += 1
    _uloz(let)
    audit.zapsat(
        kdo,
        "pristani",
        "let",
        let.pk,
        zmeny={
            "cas_pristani": let.cas_pristani.isoformat(),
            "misto_pristani": let.misto_pristani_id,
            "pocet_tg": pocet_tg,
            "kratky_let": let.kratky_let,
        },
    )
    return let


@transaction.atomic
def zrusit(let_id: int, kdo: Osoba, duvod: str, poznamka: str = "") -> Let:
    let = _zamknout(let_id)
    over_pravo(kdo, let)
    if let.stav == StavLetu.ZRUSEN:
        raise ChybaLetu("Let už je zrušený.", status=409, kod="uz_zapsano", let_id=let.pk)
    if duvod not in DuvodZruseni.values:
        raise ChybaLetu("Vyberte důvod zrušení.")
    puvodni = let.stav
    let.stav = StavLetu.ZRUSEN
    let.duvod_zruseni = duvod
    let.verze += 1
    let.save()
    audit.zapsat(
        kdo,
        "zruseni",
        "let",
        let.pk,
        zmeny={"stav": [puvodni, let.stav]},
        duvod=duvod,
        poznamka=poznamka,
    )
    return let


# --- opravy -------------------------------------------------------------------------


@dataclass
class Oprava(NovyLet):
    verze: int = 0
    duvod: str = ""
    poznamka: str = ""


def _popis(let: Let) -> dict[str, str]:
    """Čitelný stav letu pro historii změn (jména místo čísel)."""
    cas = lambda d: f"{d:%d.%m.%Y %H:%M:%S}" if d else "–"  # noqa: E731
    funkce = dict(FunkcePosadky.choices)
    return {
        "letadlo": let.letadlo.imatrikulace,
        "účel": dict(Ucel.choices)[let.ucel],
        "úloha": str(let.uloha) if let.uloha else "–",
        "způsob vzletu": dict(ZpusobVzletu.choices)[let.zpusob_vzletu],
        "posádka": ", ".join(
            f"{p.osoba.get_full_name()} ({funkce[p.funkce]})"
            for p in let.posadka.select_related("osoba").order_by("id")
        ),
        "hosté": str(let.pocet_hostu),
        "plátce": "Aeroklub" if let.plati_aeroklub else let.platce.get_full_name(),
        "místo vzletu": str(let.misto_vzletu),
        "vzlet": cas(let.cas_vzletu),
        "místo přistání": str(let.misto_pristani) if let.misto_pristani else "–",
        "přistání": cas(let.cas_pristani),
        "touch-and-go": str(let.pocet_tg),
        "krátký let": dict(KratkyLet.choices).get(let.kratky_let, "–"),
    }


def _rozdil(pred: dict, po: dict) -> dict[str, list[str]]:
    return {k: [pred[k], po[k]] for k in po if pred.get(k) != po[k]}


@transaction.atomic
def opravit(let_id: int, data: Oprava, kdo: Osoba) -> Let:
    let = _zamknout(let_id)
    over_pravo(kdo, let)
    if let.stav == StavLetu.ZRUSEN:
        raise ChybaLetu("Zrušený let nejde opravit.", status=409)
    if data.verze != let.verze:
        raise ChybaLetu(
            f"Let mezitím změnil někdo jiný{_kdo_naposledy(let, 'oprava', 'vzlet', 'pristani')}."
            " Zkontrolujte aktuální údaje a opravte znovu.",
            status=409,
            kod="zmeneno",
            let_id=let.pk,
        )
    if data.duvod not in DuvodOpravy.values:
        raise ChybaLetu("Vyberte důvod opravy.")
    if (data.ucel == Ucel.VLEK) != (let.ucel == Ucel.VLEK):
        raise ChybaLetu("Let vlečného letadla nejde opravou změnit na jiný účel ani naopak.")
    if (data.zpusob_vzletu == ZpusobVzletu.VLEK) != (let.zpusob_vzletu == ZpusobVzletu.VLEK):
        raise ChybaLetu("Vzlet ve vleku nejde opravou změnit – zrušte let a založte ho znovu.")
    data.vlek = None

    letadlo = (
        let.letadlo
        if data.letadlo_id == let.letadlo_id
        else Letadlo.objects.filter(pk=data.letadlo_id, aktivni=True).first()
    )
    if letadlo is None:
        raise ChybaLetu("Letadlo neexistuje nebo není aktivní.")
    if let.ucel == Ucel.VLEK and not letadlo.vlecne:
        raise ChybaLetu("Vybrané letadlo nemůže vlekat.")
    if data.pocet_hostu < 0 or data.pocet_tg < 0:
        raise ChybaLetu("Počty nemohou být záporné.")
    _over_posadku(data, letadlo)
    _over_platce(data)
    uloha = _over_ulohu(data, letadlo)
    _over_zpusob_vzletu(data, letadlo)

    pred = _popis(let)
    let.letadlo = letadlo
    let.soukrome = letadlo.soukrome
    let.ucel = data.ucel
    let.uloha = uloha
    let.zpusob_vzletu = data.zpusob_vzletu
    let.misto_vzletu = _letiste(data.misto_vzletu_id)
    let.pocet_hostu = data.pocet_hostu
    let.platce_id = data.platce_id
    let.plati_aeroklub = data.plati_aeroklub

    if let.stav == StavLetu.PRIPRAVEN:
        if data.cas_vzletu or data.cas_pristani:
            raise ChybaLetu("U připraveného letu se čas nezadává – použijte VZLET.")
    else:
        if not data.cas_vzletu:
            raise ChybaLetu("Zadejte čas vzletu.")
        let.cas_vzletu = _over_cas(data.cas_vzletu, "Vzlet")
        if let.stav == StavLetu.UKONCEN:
            if not data.cas_pristani:
                raise ChybaLetu("Zadejte čas přistání.")
            let.cas_pristani = _over_cas(data.cas_pristani, "Přistání")
            if let.cas_pristani < let.cas_vzletu:
                raise ChybaLetu("Přistání nemůže být dřív než vzlet.")
            let.misto_pristani = _letiste(data.misto_pristani_id)
            let.pocet_tg = data.pocet_tg
            let.kratky_let = _kratky_let(let, data.kratky_let)
        elif data.cas_pristani:
            raise ChybaLetu("Let je ještě ve vzduchu – přistání zapište tlačítkem PŘISTÁL.")
        _over_volne_osoby(_letici(data.posadka), let.cas_vzletu, let.cas_pristani, let.pk)

    let.verze += 1
    _uloz(let)
    let.posadka.all().delete()
    let.posadka.bulk_create(
        [let.posadka.model(let=let, osoba_id=c.osoba_id, funkce=c.funkce) for c in data.posadka]
    )
    zmeny = _rozdil(pred, _popis(let))
    if not zmeny:
        raise ChybaLetu("Nic se nezměnilo.")
    audit.zapsat(
        kdo, "oprava", "let", let.pk, zmeny=zmeny, duvod=data.duvod, poznamka=data.poznamka
    )
    return let


# --- tlačítko Zpět ------------------------------------------------------------------

ZPET_DO = timedelta(minutes=2)


@transaction.atomic
def zpet(let_id: int, kdo: Osoba, verze: int) -> Let:
    """Vrátí poslední akci (založení, vzlet, přistání), kterou kdo právě udělal.

    Tlačítko je vidět 10 s; server dovolí 2 minuty kvůli pomalému připojení.
    """
    let = _zamknout(let_id)
    posledni = (
        AuditLog.objects.filter(objekt="let", objekt_id=let.pk).order_by("-kdy", "-id").first()
    )
    if (
        posledni is None
        or posledni.kdo_id != kdo.pk
        or posledni.akce not in ("zalozeni", "vzlet", "pristani")
        or timezone.now() - posledni.kdy > ZPET_DO
        or let.verze != verze
    ):
        raise ChybaLetu("Akci už nejde vrátit – použijte opravu letu.", status=409, kod="nelze")

    _vratit(let, posledni.akce, kdo)
    # Založení a vzlet vleku se týkají obou letů dvojice.
    druhy = partner(let)
    if druhy is not None and posledni.akce in ("zalozeni", "vzlet"):
        druhy = _zamknout(druhy.pk)
        if (posledni.akce == "vzlet" and druhy.stav == StavLetu.VE_VZDUCHU) or (
            posledni.akce == "zalozeni" and druhy.stav != StavLetu.ZRUSEN
        ):
            _vratit(druhy, posledni.akce, kdo)
    return let


def _vratit(let: Let, akce: str, kdo: Osoba) -> None:
    pred = _popis(let)
    if akce == "pristani":
        let.stav = StavLetu.VE_VZDUCHU
        let.cas_pristani = None
        let.misto_pristani = None
        let.pocet_tg = 0
        let.kratky_let = ""
    elif akce == "vzlet":
        let.stav = StavLetu.PRIPRAVEN
        let.cas_vzletu = None
    else:  # založení omylem
        let.stav = StavLetu.ZRUSEN
        let.duvod_zruseni = DuvodZruseni.OMYL
    let.verze += 1
    _uloz(let)
    zmeny = _rozdil(pred, _popis(let))
    zmeny["vráceno"] = [akce, ""]
    audit.zapsat(kdo, "zpet", "let", let.pk, zmeny=zmeny)
