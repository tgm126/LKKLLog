from datetime import UTC, date, datetime, time, timedelta

from django.db.models import Prefetch, Q
from django.utils import timezone
from ninja import Router, Schema
from ninja.security import django_auth

from osoby.models import Kategorie, Opravneni, Osoba

from . import sluzby
from .models import (
    AuditLog,
    DuvodOpravy,
    DuvodZruseni,
    FunkcePosadky,
    KratkyLet,
    Let,
    Letadlo,
    Letiste,
    Osnova,
    Posadka,
    StavLetu,
    Ucel,
    Uloha,
    ZpusobVzletu,
)
from .slunce import slunce

router = Router(tags=["lety"], auth=django_auth)


# --- číselníky pro výběry ------------------------------------------------------


class Volba(Schema):
    hodnota: str
    nazev: str


def _volby(choices) -> list[dict]:
    return [{"hodnota": h, "nazev": n} for h, n in choices]


class LetadloOut(Schema):
    id: int
    imatrikulace: str
    typ: str
    kategorie: str
    pocet_mist: int
    max_doba_min: int | None
    soukrome: bool
    vlecne: bool


class OpravneniOut(Schema):
    kategorie: str
    uroven: str


class OsobaOut(Schema):
    id: int
    jmeno: str
    prijmeni: str
    externi: bool
    opravneni: list[OpravneniOut]


class LetisteOut(Schema):
    id: int
    icao: str | None
    nazev: str
    domovske: bool
    teren: bool


class UlohaOut(Schema):
    id: int
    kod: str
    nazev: str
    ucely: list[str]


class OsnovaOut(Schema):
    id: int
    kategorie: str
    nazev: str
    ulohy: list[UlohaOut]


class CiselnikyOut(Schema):
    letadla: list[LetadloOut]
    osoby: list[OsobaOut]
    letiste: list[LetisteOut]
    osnovy: list[OsnovaOut]
    kategorie: list[Volba]
    ucely: list[Volba]
    funkce: list[Volba]
    zpusoby_vzletu: list[Volba]
    duvody_zruseni: list[Volba]
    duvody_opravy: list[Volba]
    kratke_lety: list[Volba]


@router.get("/ciselniky", response=CiselnikyOut, summary="Vše pro výběry v aplikaci")
def ciselniky(request):
    # Telefon se tu záměrně neposílá – jen na vyžádání (viz návrh).
    osoby = (
        Osoba.objects.filter(is_active=True)
        .only("id", "jmeno", "prijmeni", "externi")
        .prefetch_related(
            Prefetch(
                "opravneni", queryset=Opravneni.objects.only("osoba_id", "kategorie", "uroven")
            )
        )
    )
    osnovy = Osnova.objects.filter(aktivni=True).prefetch_related(
        Prefetch("ulohy", queryset=Uloha.objects.filter(aktivni=True))
    )
    return {
        "letadla": Letadlo.objects.filter(aktivni=True),
        "osoby": [
            {
                "id": o.pk,
                "jmeno": o.jmeno,
                "prijmeni": o.prijmeni,
                "externi": o.externi,
                "opravneni": list(o.opravneni.all()),
            }
            for o in osoby
        ],
        "letiste": Letiste.objects.filter(aktivni=True),
        "osnovy": [
            {"id": o.pk, "kategorie": o.kategorie, "nazev": o.nazev, "ulohy": list(o.ulohy.all())}
            for o in osnovy
        ],
        "kategorie": _volby(Kategorie.choices),
        "ucely": _volby(Ucel.choices),
        "funkce": _volby(FunkcePosadky.choices),
        "zpusoby_vzletu": _volby(ZpusobVzletu.choices),
        "duvody_zruseni": _volby(DuvodZruseni.choices),
        "duvody_opravy": _volby(DuvodOpravy.choices),
        "kratke_lety": _volby(KratkyLet.choices),
    }


# --- přehled dne ----------------------------------------------------------------


class ClenOut(Schema):
    osoba_id: int
    jmeno: str
    funkce: str


class LetOut(Schema):
    id: int
    stav: str
    letadlo_id: int
    imatrikulace: str
    typ: str
    kategorie: str
    max_doba_min: int | None
    ucel: str
    uloha: str | None
    uloha_id: int | None
    zpusob_vzletu: str
    posadka: list[ClenOut]
    pocet_hostu: int
    platce: str | None
    platce_id: int | None
    plati_aeroklub: bool
    misto_vzletu: str
    misto_vzletu_id: int
    misto_pristani: str | None
    misto_pristani_id: int | None
    cas_vzletu: datetime | None
    cas_pristani: datetime | None
    doba_min: int | None
    doba_uctovana_min: int | None
    pocet_tg: int
    kratky_let: str
    duvod_zruseni: str
    zalozil: str
    dodatecne: bool
    verze: int
    muze_ovladat: bool
    vlek_id: int | None
    vlek: str | None


def _misto(letiste: Letiste | None) -> str | None:
    if letiste is None:
        return None
    return letiste.icao or letiste.nazev


def _let_out(let: Let, osoba: Osoba) -> dict:
    return {
        "id": let.pk,
        "stav": let.stav,
        "letadlo_id": let.letadlo_id,
        "imatrikulace": let.letadlo.imatrikulace,
        "typ": let.letadlo.typ,
        "kategorie": let.letadlo.kategorie,
        "max_doba_min": let.letadlo.max_doba_min,
        "ucel": let.ucel,
        "uloha": str(let.uloha) if let.uloha else None,
        "uloha_id": let.uloha_id,
        "zpusob_vzletu": let.zpusob_vzletu,
        "posadka": [
            {"osoba_id": p.osoba_id, "jmeno": p.osoba.get_full_name(), "funkce": p.funkce}
            for p in let.posadka.all()
        ],
        "pocet_hostu": let.pocet_hostu,
        "platce": let.platce.get_full_name() if let.platce else None,
        "platce_id": let.platce_id,
        "plati_aeroklub": let.plati_aeroklub,
        "misto_vzletu": _misto(let.misto_vzletu),
        "misto_vzletu_id": let.misto_vzletu_id,
        "misto_pristani": _misto(let.misto_pristani),
        "misto_pristani_id": let.misto_pristani_id,
        "cas_vzletu": let.cas_vzletu,
        "cas_pristani": let.cas_pristani,
        "doba_min": let.doba_min,
        "doba_uctovana_min": let.doba_uctovana_min,
        "pocet_tg": let.pocet_tg,
        "kratky_let": let.kratky_let,
        "duvod_zruseni": let.duvod_zruseni,
        "zalozil": let.zalozil.get_full_name(),
        "dodatecne": bool(let.cas_pristani and let.zalozeno > let.cas_pristani),
        "verze": let.verze,
        "muze_ovladat": sluzby.muze_ovladat(osoba, let),
        **_dvojice(let),
    }


def _dvojice(let: Let) -> dict:
    """Druhý let z dvojice vleku: u kluzáku vlečná a vlekař, u vlečné vlečený kluzák."""
    if let.vlecny_let_id:
        druhy, popis = let.vlecny_let, "vlek"
    else:
        druhy = getattr(let, "vleceny_let", None)
        popis = "vleče"
    if druhy is None:
        return {"vlek_id": None, "vlek": None}
    pic = next((p.osoba.get_full_name() for p in druhy.posadka.all() if p.funkce == "pic"), "")
    return {"vlek_id": druhy.pk, "vlek": f"{popis} {druhy.letadlo.imatrikulace} ({pic})"}


def _lety():
    posadka = Posadka.objects.select_related("osoba").order_by("id")
    return Let.objects.select_related(
        "letadlo",
        "uloha",
        "platce",
        "misto_vzletu",
        "misto_pristani",
        "zalozil",
        "vlecny_let__letadlo",
        "vleceny_let__letadlo",
    ).prefetch_related(
        Prefetch("posadka", queryset=posadka),
        Prefetch("vlecny_let__posadka", queryset=posadka),
        Prefetch("vleceny_let__posadka", queryset=posadka),
    )


class PrehledOut(Schema):
    den: date
    ted: datetime
    zapad_slunce: datetime
    konec_soumraku: datetime
    lety: list[LetOut]


@router.get("/prehled", response=PrehledOut, summary="Přehled dne (UTC)")
def prehled(request, den: date | None = None):
    ted = timezone.now()
    den = den or ted.date()
    zacatek = datetime.combine(den, time.min, tzinfo=UTC)
    podminka = Q(cas_vzletu__gte=zacatek, cas_vzletu__lt=zacatek + timedelta(days=1))
    if den == ted.date():
        # Dnes ukazujeme i všechno, co ještě neskončilo (připravené a ve vzduchu).
        podminka |= Q(stav__in=[StavLetu.PRIPRAVEN, StavLetu.VE_VZDUCHU])
    lety = _lety().filter(podminka).order_by("cas_vzletu", "id")
    udaje = slunce(den)
    return {
        "den": den,
        "ted": ted,
        "zapad_slunce": udaje["zapad"],
        "konec_soumraku": udaje["soumrak"],
        "lety": [_let_out(let, request.user) for let in lety],
    }


@router.get("/lety/{let_id}", response=LetOut, summary="Detail letu")
def detail(request, let_id: int):
    let = _lety().filter(pk=let_id).first()
    if let is None:
        raise sluzby.ChybaLetu("Let neexistuje.", status=404)
    return _let_out(let, request.user)


# --- akce s letem ---------------------------------------------------------------


class ClenIn(Schema):
    osoba_id: int
    funkce: str


class VlekIn(Schema):
    letadlo_id: int
    vlekar_id: int
    cas_pristani: datetime | None = None


class NovyLetIn(Schema):
    letadlo_id: int
    ucel: str
    posadka: list[ClenIn]
    uloha_id: int | None = None
    zpusob_vzletu: str = ZpusobVzletu.VLASTNI
    misto_vzletu_id: int | None = None
    pocet_hostu: int = 0
    platce_id: int | None = None
    plati_aeroklub: bool = False
    akce: str = "vzlet"
    cas_vzletu: datetime | None = None
    cas_pristani: datetime | None = None
    misto_pristani_id: int | None = None
    pocet_tg: int = 0
    kratky_let: str = ""
    vlek: VlekIn | None = None


def _znovu(let: Let, osoba: Osoba) -> dict:
    return _let_out(_lety().get(pk=let.pk), osoba)


@router.post("/lety", response=LetOut, summary="Založit let")
def zalozit(request, data: NovyLetIn):
    vstup = data.dict()
    vstup["posadka"] = [sluzby.ClenPosadky(**c) for c in vstup["posadka"]]
    let = sluzby.zalozit(sluzby.NovyLet(**vstup), request.user)
    return _znovu(let, request.user)


class CasIn(Schema):
    cas: datetime | None = None


@router.post("/lety/{let_id}/vzlet", response=LetOut, summary="Vzlet (teď nebo v čase)")
def vzlet(request, let_id: int, data: CasIn):
    return _znovu(sluzby.vzlet(let_id, request.user, data.cas), request.user)


class PristaniIn(Schema):
    cas: datetime | None = None
    misto_pristani_id: int | None = None
    pocet_tg: int = 0
    kratky_let: str = ""


@router.post("/lety/{let_id}/pristani", response=LetOut, summary="Přistání")
def pristani(request, let_id: int, data: PristaniIn):
    let = sluzby.pristani(
        let_id, request.user, data.cas, data.misto_pristani_id, data.pocet_tg, data.kratky_let
    )
    return _znovu(let, request.user)


class ZruseniIn(Schema):
    duvod: str
    poznamka: str = ""


@router.post("/lety/{let_id}/zrusit", response=LetOut, summary="Zrušit let (s důvodem)")
def zrusit(request, let_id: int, data: ZruseniIn):
    return _znovu(sluzby.zrusit(let_id, request.user, data.duvod, data.poznamka), request.user)


class OpravaIn(NovyLetIn):
    verze: int
    duvod: str
    poznamka: str = ""


@router.post("/lety/{let_id}/oprava", response=LetOut, summary="Opravit let (s důvodem)")
def opravit(request, let_id: int, data: OpravaIn):
    vstup = data.dict()
    vstup.pop("akce", None)
    vstup["posadka"] = [sluzby.ClenPosadky(**c) for c in vstup["posadka"]]
    let = sluzby.opravit(let_id, sluzby.Oprava(**vstup), request.user)
    return _znovu(let, request.user)


class VerzeIn(Schema):
    verze: int


@router.post("/lety/{let_id}/zpet", response=LetOut, summary="Vrátit poslední akci (Zpět)")
def zpet(request, let_id: int, data: VerzeIn):
    return _znovu(sluzby.zpet(let_id, request.user, data.verze), request.user)


class ZaznamOut(Schema):
    kdy: datetime
    kdo: str
    akce: str
    zmeny: dict
    duvod: str
    poznamka: str


NAZVY_AKCI = {
    "zalozeni": "Založení",
    "vzlet": "Vzlet",
    "pristani": "Přistání",
    "zruseni": "Zrušení",
    "oprava": "Oprava",
    "zpet": "Vráceno tlačítkem Zpět",
}


@router.get("/lety/{let_id}/historie", response=list[ZaznamOut], summary="Historie změn letu")
def historie(request, let_id: int):
    duvody = dict(DuvodOpravy.choices) | dict(DuvodZruseni.choices)
    zaznamy = (
        AuditLog.objects.select_related("kdo")
        .filter(objekt="let", objekt_id=let_id)
        .order_by("kdy", "id")
    )
    return [
        {
            "kdy": z.kdy,
            "kdo": z.kdo.get_full_name() if z.kdo else "systém",
            "akce": NAZVY_AKCI.get(z.akce, z.akce),
            "zmeny": z.zmeny,
            "duvod": duvody.get(z.duvod, z.duvod),
            "poznamka": z.poznamka,
        }
        for z in zaznamy
    ]
