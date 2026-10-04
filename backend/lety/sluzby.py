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
    DuvodZruseni,
    FunkcePosadky,
    KratkyLet,
    Let,
    Letadlo,
    Letiste,
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
    osoby: dict[int, Osoba] = field(default_factory=dict)


def _over_posadku(data: NovyLet, letadlo: Letadlo) -> None:
    if data.ucel == Ucel.VLEK:
        raise ChybaLetu("Vlek se zakládá spolu s kluzákem (připravujeme).")
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
        if data.zpusob_vzletu == ZpusobVzletu.VLEK:
            raise ChybaLetu("Vlek se zakládá spolu s vlečným letadlem (připravujeme).")
        if data.zpusob_vzletu not in (ZpusobVzletu.NAVIJAK, ZpusobVzletu.AUTOSTART):
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


@transaction.atomic
def zalozit(data: NovyLet, kdo: Osoba) -> Let:
    letadlo = Letadlo.objects.filter(pk=data.letadlo_id, aktivni=True).first()
    if letadlo is None:
        raise ChybaLetu("Letadlo neexistuje nebo není aktivní.")
    if data.pocet_hostu < 0 or data.pocet_tg < 0:
        raise ChybaLetu("Počty nemohou být záporné.")
    _over_posadku(data, letadlo)
    _over_platce(data)
    uloha = _over_ulohu(data, letadlo)
    _over_zpusob_vzletu(data, letadlo)

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


def _kdo_naposledy(let: Let, akce: str) -> str:
    from .models import AuditLog

    zaznam = (
        AuditLog.objects.select_related("kdo")
        .filter(objekt="let", objekt_id=let.pk, akce=akce)
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
            f"Vzlet už je zapsaný v {let.cas_vzletu:%H:%M:%S} UTC{_kdo_naposledy(let, 'vzlet')}.",
            status=409,
            kod="uz_zapsano",
            let_id=let.pk,
        )
    let.cas_vzletu = _over_cas(cas or timezone.now(), "Vzlet")
    let.stav = StavLetu.VE_VZDUCHU
    let.verze += 1
    _uloz(let)
    audit.zapsat(kdo, "vzlet", "let", let.pk, zmeny={"cas_vzletu": let.cas_vzletu.isoformat()})
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
            f"Přistání už je zapsané{konec}{_kdo_naposledy(let, 'pristani')}.",
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
