import secrets
from datetime import UTC, date, datetime, time, timedelta

from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.utils import timezone
from ninja import Router, Schema
from ninja.security import django_auth

from osoby.models import Kategorie, Licence, Opravneni, Osoba, TypLicence, smi_spravovat_licence
from provoz.models import Nastaveni

from . import audit, letadla, nalet, obdobi, rozletanost, sluzby, uzaverky, vypis
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
    TerminLetadla,
    Ucel,
    Uloha,
    Uzaverka,
    ZpusobVzletu,
)
from .obdobi import Uzavreno
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
    casy_tg: list[datetime]
    pocet_pristani: int
    kratky_let: str
    duvod_zruseni: str
    zalozil: str
    dodatecne: bool
    verze: int
    muze_ovladat: bool
    opraveno_po_uzaverce: bool
    vlek_id: int | None
    vlek: str | None


def _misto(letiste: Letiste | None) -> str | None:
    if letiste is None:
        return None
    return letiste.icao or letiste.nazev


def _let_out(let: Let, osoba: Osoba | None, uzavreno: Uzavreno | None = None) -> dict:
    """Let pro frontend; bez osoby (displej) nikdo nic neovládá."""
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
        "casy_tg": let.casy_tg,
        "pocet_pristani": let.pocet_pristani,
        "kratky_let": let.kratky_let,
        "duvod_zruseni": let.duvod_zruseni,
        "zalozil": let.zalozil.get_full_name(),
        "dodatecne": bool(let.cas_pristani and let.zalozeno > let.cas_pristani),
        "verze": let.verze,
        "muze_ovladat": osoba is not None and sluzby.muze_ovladat(osoba, let, uzavreno),
        "opraveno_po_uzaverce": let.opraveno_po_uzaverce,
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


class UzaverkaOut(Schema):
    id: int
    typ: str
    obdobi: date
    verze: int
    kdy: datetime
    uzavrel: str
    platna: bool


class StavDneOut(Schema):
    uzaverka: UzaverkaOut | None
    mesic_uzavren: bool
    zmeny: int
    smi_uzavrit: bool


def _lety_dne(den: date, ted: datetime) -> list[Let]:
    zacatek = datetime.combine(den, time.min, tzinfo=UTC)
    podminka = Q(cas_vzletu__gte=zacatek, cas_vzletu__lt=zacatek + timedelta(days=1))
    if den == ted.date():
        # Dnes ukazujeme i všechno, co ještě neskončilo (připravené a ve vzduchu).
        podminka |= Q(stav__in=[StavLetu.PRIPRAVEN, StavLetu.VE_VZDUCHU])
    return list(_lety().filter(podminka).order_by("cas_vzletu", "id"))


class PrehledOut(Schema):
    den: date
    ted: datetime
    zapad_slunce: datetime
    konec_soumraku: datetime
    lety: list[LetOut]
    uzaverka: StavDneOut


@router.get("/prehled", response=PrehledOut, summary="Přehled dne (UTC)")
def prehled(request, den: date | None = None):
    ted = timezone.now()
    den = den or ted.date()
    lety = _lety_dne(den, ted)
    udaje = slunce(den)
    uzavreno = Uzavreno.nacti()
    return {
        "den": den,
        "ted": ted,
        "zapad_slunce": udaje["zapad"],
        "konec_soumraku": udaje["soumrak"],
        "lety": [_let_out(let, request.user, uzavreno) for let in lety],
        "uzaverka": uzaverky.stav_dne(den, request.user),
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


@router.post("/lety/{let_id}/tg", response=LetOut, summary="Touch-and-go během letu")
def touch_and_go(request, let_id: int):
    return _znovu(sluzby.touch_and_go(let_id, request.user), request.user)


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
    "tg": "Touch-and-go",
    "pristani": "Přistání",
    "zruseni": "Zrušení",
    "oprava": "Oprava",
    "zpet": "Vráceno tlačítkem Zpět",
    "upozorneni": "Odesláno upozornění",
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


# --- výpis a export (etapa 7) -----------------------------------------------------------


class VypisOut(Schema):
    od: date
    do: date
    lety: list[LetOut]
    souhrn: dict
    smi_exportovat: bool


def _filtr(
    od: date | None,
    do: date | None,
    letadlo: int | None,
    osoba: int | None,
    platce: int | None,
    kategorie: str | None,
    ucel: str | None,
    zpusob: str | None,
    soukrome: bool,
    zrusene: bool,
) -> vypis.Filtr:
    dnes = timezone.now().date()
    od = od or dnes.replace(day=1)
    return vypis.Filtr(
        od=od,
        do=do or dnes,
        letadlo_id=letadlo,
        osoba_id=osoba,
        platce_id=platce,
        kategorie=kategorie or None,
        ucel=ucel or None,
        zpusob_vzletu=zpusob or None,
        vcetne_soukromych=soukrome,
        vcetne_zrusenych=zrusene,
    )


def _nacti(request, **parametry) -> tuple[vypis.Filtr, list[Let]]:
    filtr = _filtr(**parametry)
    try:
        return filtr, vypis.lety(filtr, _lety().select_related("vlecny_let__letadlo"))
    except vypis.ChybaVypisu as e:
        raise sluzby.ChybaLetu(str(e)) from e


@router.get("/vypis", response=VypisOut, summary="Výpis letů za období se souhrny")
def vypis_letu(
    request,
    od: date | None = None,
    do: date | None = None,
    letadlo: int | None = None,
    osoba: int | None = None,
    platce: int | None = None,
    kategorie: str | None = None,
    ucel: str | None = None,
    zpusob: str | None = None,
    soukrome: bool = False,
    zrusene: bool = False,
):
    filtr, seznam = _nacti(
        request,
        od=od,
        do=do,
        letadlo=letadlo,
        osoba=osoba,
        platce=platce,
        kategorie=kategorie,
        ucel=ucel,
        zpusob=zpusob,
        soukrome=soukrome,
        zrusene=zrusene,
    )
    uzavreno = Uzavreno.nacti()
    return {
        "od": filtr.od,
        "do": filtr.do,
        "lety": [_let_out(let, request.user, uzavreno) for let in seznam],
        "souhrn": vypis.souhrn(seznam),
        "smi_exportovat": vypis.smi_exportovat(request.user),
    }


def _nazvy(filtr: vypis.Filtr) -> dict:
    letadlo = Letadlo.objects.filter(pk=filtr.letadlo_id).first() if filtr.letadlo_id else None
    osoba = Osoba.objects.filter(pk=filtr.osoba_id).first() if filtr.osoba_id else None
    platce = Osoba.objects.filter(pk=filtr.platce_id).first() if filtr.platce_id else None
    return {
        "letadlo": letadlo.imatrikulace if letadlo else None,
        "osoba": osoba.get_full_name() if osoba else None,
        "platce": "Aeroklub"
        if filtr.platce_id == 0
        else (platce.get_full_name() if platce else None),
    }


@router.get("/vypis/export.{format}", summary="Export výpisu do Excelu nebo CSV")
def export(
    request,
    format: str,
    od: date | None = None,
    do: date | None = None,
    letadlo: int | None = None,
    osoba: int | None = None,
    platce: int | None = None,
    kategorie: str | None = None,
    ucel: str | None = None,
    zpusob: str | None = None,
    soukrome: bool = False,
    zrusene: bool = False,
):
    if not vypis.smi_exportovat(request.user):
        raise sluzby.ChybaLetu("Export smí stahovat účetní a admin.", status=403)
    if format not in ("xlsx", "csv"):
        raise sluzby.ChybaLetu("Neznámý formát exportu.", status=404)
    filtr, seznam = _nacti(
        request,
        od=od,
        do=do,
        letadlo=letadlo,
        osoba=osoba,
        platce=platce,
        kategorie=kategorie,
        ucel=ucel,
        zpusob=zpusob,
        soukrome=soukrome,
        zrusene=zrusene,
    )
    nazev = f"lkkllog-vypis-{filtr.od:%Y-%m-%d}-{filtr.do:%Y-%m-%d}.{format}"
    if format == "xlsx":
        obsah = vypis.excel(seznam, filtr, _nazvy(filtr), request.user.get_full_name())
        typ = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        obsah, typ = vypis.csv_data(seznam), "text/csv; charset=utf-8"
    odpoved = HttpResponse(obsah, content_type=typ)
    odpoved["Content-Disposition"] = f'attachment; filename="{nazev}"'
    return odpoved


# --- uzávěrky (etapa 8) -------------------------------------------------------------------


class DenMesiceOut(Schema):
    den: date
    lety: int
    minuty: int
    neukonceno: int
    uzaverka: UzaverkaOut | None
    zmeny: int
    smi_uzavrit: bool


class MesicOut(Schema):
    mesic: date
    dny: list[DenMesiceOut]
    uzaverka: UzaverkaOut | None
    zmeny: int
    skoncil: bool
    smi_uzavrit: bool


@router.get("/uzaverky", response=MesicOut, summary="Dny měsíce a stav jejich uzávěrek")
def prehled_uzaverek(request, mesic: date | None = None):
    return uzaverky.prehled_mesice(mesic or timezone.now().date(), request.user)


class NahledOut(Schema):
    typ: str
    obdobi: date
    souhrn: dict
    lze: bool
    zakaz: str | None
    neukonceno: list[str]
    neuzavrene_dny: list[date]
    posledni: UzaverkaOut | None
    dnes: bool


@router.get("/uzaverky/nahled", response=NahledOut, summary="Souhrn před uzavřením")
def nahled_uzaverky(request, typ: str, obdobi: date):
    p = uzaverky.priprav(typ, obdobi, request.user)
    return {
        "typ": p.typ,
        "obdobi": p.obdobi,
        "souhrn": uzaverky.souhrn(p.seznam),
        "lze": p.lze,
        "zakaz": p.zakaz,
        "neukonceno": p.neukonceno,
        "neuzavrene_dny": p.neuzavrene_dny,
        "posledni": uzaverky.info(p.posledni),
        "dnes": p.typ == Uzaverka.Typ.DEN and p.obdobi == timezone.now().date(),
    }


class UzavritIn(Schema):
    typ: str
    obdobi: date


@router.post("/uzaverky", response=UzaverkaOut, summary="Uzavřít den / měsíc (nebo přepočítat)")
def uzavrit(request, data: UzavritIn):
    return uzaverky.info(uzaverky.uzavrit(data.typ, data.obdobi, request.user))


class ZaznamZmenyOut(Schema):
    kdy: datetime
    kdo: str
    akce: str
    zmeny: dict
    duvod: str
    poznamka: str


class ZmenenyLetOut(Schema):
    id: int
    imatrikulace: str
    cas_vzletu: datetime | None
    cas_pristani: datetime | None
    stav: str
    doba_uctovana_min: int | None
    zaznamy: list[ZaznamZmenyOut]


class DetailUzaverkyOut(Schema):
    typ: str
    obdobi: date
    verze: list[UzaverkaOut]
    souhrn: dict | None
    rozdil: dict | None
    lety: list[ZmenenyLetOut]


@router.get("/uzaverky/detail", response=DetailUzaverkyOut, summary="Verze a změny po uzávěrce")
def detail_uzaverky(request, typ: str, obdobi: date):
    vysledek = uzaverky.detail(typ, obdobi)
    duvody = dict(DuvodOpravy.choices) | dict(DuvodZruseni.choices)
    for let in vysledek["lety"]:
        for z in let["zaznamy"]:
            z["duvod"] = duvody.get(z["duvod"], z["duvod"])
    return vysledek


@router.get("/uzaverky/{uzaverka_id}/export.xlsx", summary="Souhrn uzávěrky do Excelu")
def export_uzaverky(request, uzaverka_id: int):
    if not vypis.smi_exportovat(request.user):
        raise sluzby.ChybaLetu("Export smí stahovat účetní a admin.", status=403)
    u = Uzaverka.objects.select_related("uzavrel").filter(pk=uzaverka_id).first()
    if u is None:
        raise sluzby.ChybaLetu("Uzávěrka neexistuje.", status=404)
    obdobi = f"{u.obdobi:%Y-%m-%d}" if u.typ == Uzaverka.Typ.DEN else f"{u.obdobi:%Y-%m}"
    odpoved = HttpResponse(
        uzaverky.excel(u),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    nazev = f"lkkllog-uzaverka-{obdobi}-v{u.verze}.xlsx"
    odpoved["Content-Disposition"] = f'attachment; filename="{nazev}"'
    return odpoved


# --- velký displej (etapa 9) --------------------------------------------------------------


class DisplejClenOut(Schema):
    jmeno: str
    funkce: str
    funkce_nazev: str


class DisplejLetOut(Schema):
    """Jen to, co patří na veřejnou obrazovku (žádné telefony, plátci ani ovládání).

    Názvy účelu a funkcí posílá server, displej nemá přístup k číselníkům.
    """

    id: int
    stav: str
    imatrikulace: str
    typ: str
    kategorie: str
    max_doba_min: int | None
    ucel: str
    ucel_nazev: str
    zpusob_vzletu: str
    zpusob_nazev: str
    posadka: list[DisplejClenOut]
    pocet_hostu: int
    misto_vzletu: str
    misto_pristani: str | None
    cas_vzletu: datetime | None
    cas_pristani: datetime | None
    doba_uctovana_min: int | None
    pocet_tg: int
    casy_tg: list[datetime]
    pocet_pristani: int
    duvod_zruseni: str
    vlek_id: int | None
    vlek: str | None


class DisplejOut(Schema):
    den: date
    ted: datetime
    zapad_slunce: datetime
    konec_soumraku: datetime
    lety: list[DisplejLetOut]
    souhrn: dict


@router.get("/displej", response=DisplejOut, auth=None, summary="Data pro velký displej")
def displej(request, klic: str = ""):
    """Bez přihlášení, jen s tajným klíčem z Nastavení provozu (lze kdykoli zneplatnit)."""
    platny = Nastaveni.aktualni().displej_klic
    if not (klic and platny and secrets.compare_digest(klic, platny)):
        raise sluzby.ChybaLetu("Odkaz na displej neplatí.", status=404, kod="displej")
    ted = timezone.now()
    den = ted.date()
    lety = _lety_dne(den, ted)
    udaje = slunce(den)
    return {
        "den": den,
        "ted": ted,
        "zapad_slunce": udaje["zapad"],
        "konec_soumraku": udaje["soumrak"],
        "lety": [_let_displej(let) for let in lety],
        "souhrn": vypis.souhrn([let for let in lety if obdobi.den_letu(let) == den]),
    }


def _let_displej(let: Let) -> dict:
    data = _let_out(let, None)
    funkce = dict(FunkcePosadky.choices)
    data["ucel_nazev"] = dict(Ucel.choices)[let.ucel]
    data["zpusob_nazev"] = dict(ZpusobVzletu.choices)[let.zpusob_vzletu]
    for clen in data["posadka"]:
        clen["funkce_nazev"] = funkce[clen["funkce"]]
    return data


# --- můj nálet (etapa 11) -----------------------------------------------------------------


class MujLetOut(LetOut):
    moje_funkce: str


class NaletOut(Schema):
    od: date
    do: date
    souhrn: dict
    lety: list[MujLetOut]


def _muj_nalet(request, od: date | None, do: date | None):
    dnes = timezone.now().date()
    od = od or dnes.replace(month=1, day=1)
    do = do or dnes
    return od, do, nalet.lety(request.user, od, do, _lety())


@router.get("/nalet", response=NaletOut, summary="Můj nálet za období (neoficiální)")
def muj_nalet(request, od: date | None = None, do: date | None = None):
    od, do, seznam = _muj_nalet(request, od, do)
    uzavreno = Uzavreno.nacti()
    return {
        "od": od,
        "do": do,
        "souhrn": nalet.souhrn(seznam),
        "lety": [
            {**_let_out(m.let, request.user, uzavreno), "moje_funkce": m.funkce}
            for m in reversed(seznam)  # nejnovější nahoře
        ],
    }


@router.get("/nalet/export.xlsx", summary="Můj nálet do Excelu")
def export_naletu(request, od: date | None = None, do: date | None = None):
    od, do, seznam = _muj_nalet(request, od, do)
    odpoved = HttpResponse(
        nalet.excel(request.user, seznam, od, do),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    nazev = f"lkkllog-nalet-{od:%Y-%m-%d}-{do:%Y-%m-%d}.xlsx"
    odpoved["Content-Disposition"] = f'attachment; filename="{nazev}"'
    return odpoved


# --- licence, medical a rozlétanost (etapa 12) ----------------------------------------------


class KontrolaOut(Schema):
    oblast: str
    nazev: str
    stav: str
    text: str
    plati_do: date | None
    podrobnosti: list[str]
    modul: str


class ModulyOut(Schema):
    zpusobilost: bool
    rozletanost: bool


class RozletanostOut(Schema):
    moduly: ModulyOut
    zobrazit: bool
    kontroly: list[KontrolaOut]


def _moduly_pilotu() -> frozenset:
    nastaveni = Nastaveni.aktualni()
    return frozenset(
        m
        for m, zapnuto in (
            (rozletanost.ZPUSOBILOST, nastaveni.hlidat_zpusobilost),
            (rozletanost.ROZLETANOST, nastaveni.hlidat_rozletanost),
        )
        if zapnuto
    )


@router.get("/nalet/rozletanost", response=RozletanostOut, summary="Moje licence a rozlétanost")
def moje_rozletanost(request):
    """Pilot vidí kontroly zapnutých modulů; admin všechny (kontrola dat před zapnutím)."""
    moduly = _moduly_pilotu()
    kontroly = rozletanost.kontroly(request.user) if moduly or request.user.is_staff else []
    if not request.user.is_staff:
        kontroly = [k for k in kontroly if k.modul in moduly]
    return {
        "moduly": {m: m in moduly for m in (rozletanost.ZPUSOBILOST, rozletanost.ROZLETANOST)},
        "zobrazit": bool(kontroly) or bool(moduly),
        "kontroly": kontroly,
    }


class KontrolaLetuIn(Schema):
    letadlo_id: int
    ucel: str = Ucel.NORMALNI
    posadka: list[ClenIn]
    pocet_hostu: int = 0
    zpusob_vzletu: str = ZpusobVzletu.VLASTNI
    vlek: VlekIn | None = None


class VarovaniOut(Schema):
    varovani: list[str]


@router.post("/kontrola-posadky", response=VarovaniOut, summary="Varování k posádce před letem")
def kontrola_letu(request, data: KontrolaLetuIn):
    """Letadlo, licence, medical a rozlétanost PIC (a vlekaře) podle zapnutých modulů.

    Jen varuje, nic neblokuje.
    """
    moduly = _moduly_pilotu()
    varovani = []
    if Nastaveni.aktualni().hlidat_letadla:
        varovani += letadla.varovani_letadla(data.letadlo_id)
        if data.vlek:
            varovani += letadla.varovani_letadla(data.vlek.letadlo_id)
    if not moduly:
        return {"varovani": varovani}
    letadlo = Letadlo.objects.filter(pk=data.letadlo_id).first()
    pic = next((c for c in data.posadka if c.funkce == FunkcePosadky.PIC), None)
    if letadlo and pic and (osoba := Osoba.objects.filter(pk=pic.osoba_id).first()):
        cestujici = data.pocet_hostu > 0 or any(
            c.funkce == FunkcePosadky.CLEN for c in data.posadka
        )
        if data.ucel == Ucel.VYCVIK_SOLO:  # PIC je žák: licenci ani rozlétanost ještě nemá
            if rozletanost.ZPUSOBILOST in moduly:
                varovani += rozletanost.varovani_pred_solem(osoba)
        else:
            varovani += rozletanost.varovani_pilota(
                osoba, letadlo.kategorie, cestujici, data.zpusob_vzletu, moduly
            )
    if data.vlek and (vlekar := Osoba.objects.filter(pk=data.vlek.vlekar_id).first()):
        vlecne = Letadlo.objects.filter(pk=data.vlek.letadlo_id).first()
        if vlecne:
            varovani += rozletanost.varovani_pilota(vlekar, vlecne.kategorie, False, moduly=moduly)
    return {"varovani": varovani}


# --- přehled pilotů a letadel pro správce (etapa 13) ----------------------------------------


def _jen_spravce(request):
    if not smi_spravovat_licence(request.user):
        raise sluzby.ChybaLetu("Přehled je pro správce licencí a letadel a admina.", status=403)


class PilotOut(Schema):
    id: int
    jmeno: str
    licence: list[str]
    stav: str
    problemy: list[str]


@router.get("/sprava/piloti", response=list[PilotOut], summary="Přehled pilotů (správce)")
def sprava_piloti(request):
    """Piloti = aktivní členové s licencí nebo oprávněním (bez externích a testovacích)."""
    _jen_spravce(request)
    typy = dict(TypLicence.choices)
    osoby = (
        Osoba.objects.filter(is_active=True, externi=False, testovaci=False)
        .filter(Q(licence__isnull=False) | Q(opravneni__isnull=False))
        .distinct()
        .order_by("prijmeni", "jmeno")
    )
    poradi = [rozletanost.OK, rozletanost.INFO, rozletanost.POZOR, rozletanost.CHYBA]
    vysledek = []
    for o in osoby:
        kontroly = rozletanost.kontroly(o)
        vysledek.append(
            {
                "id": o.pk,
                "jmeno": o.get_full_name(),
                "licence": [typy[lic.typ] for lic in Licence.objects.filter(osoba=o)],
                "stav": max((k.stav for k in kontroly), key=poradi.index),
                "problemy": [
                    f"{k.nazev}: {k.text}"
                    for k in kontroly
                    if k.stav in (rozletanost.POZOR, rozletanost.CHYBA)
                ],
            }
        )
    return vysledek


@router.get("/sprava/piloti/{osoba_id}", response=RozletanostOut, summary="Rozlétanost pilota")
def sprava_pilot(request, osoba_id: int):
    _jen_spravce(request)
    osoba = Osoba.objects.filter(pk=osoba_id).first()
    if osoba is None:
        raise sluzby.ChybaLetu("Osoba neexistuje.", status=404)
    return {
        "moduly": {"zpusobilost": True, "rozletanost": True},
        "zobrazit": True,
        "kontroly": rozletanost.kontroly(osoba),
    }


class TerminOut(Schema):
    id: int
    nazev: str
    datum: date | None
    pri_naletu_h: int | None
    poznamka: str
    stav: str
    text: str


class LetadloSpravaOut(Schema):
    id: int
    imatrikulace: str
    typ: str
    kategorie: str
    nalet_min: int
    starty: int
    nalet_pocatek_min: int
    starty_pocatek: int
    stav_k: date | None
    chybi_denik: bool
    terminy: list[TerminOut]


@router.get("/sprava/letadla", response=list[LetadloSpravaOut], summary="Letadla a termíny")
def sprava_letadla(request):
    _jen_spravce(request)
    return letadla.prehled()


class StavDenikuIn(Schema):
    nalet_pocatek_min: int
    starty_pocatek: int
    stav_k: date | None = None


@router.post("/sprava/letadla/{letadlo_id}/denik", response=list[LetadloSpravaOut])
def sprava_denik(request, letadlo_id: int, data: StavDenikuIn):
    """Stav z provozního deníku letadla; lety po tomto dni se přičítají z evidence."""
    _jen_spravce(request)
    if data.nalet_pocatek_min < 0 or data.starty_pocatek < 0:
        raise sluzby.ChybaLetu("Hodnoty nemohou být záporné.")
    letadlo = Letadlo.objects.filter(pk=letadlo_id).first()
    if letadlo is None:
        raise sluzby.ChybaLetu("Letadlo neexistuje.", status=404)
    letadlo.nalet_pocatek_min = data.nalet_pocatek_min
    letadlo.starty_pocatek = data.starty_pocatek
    letadlo.stav_k = data.stav_k
    letadlo.save(update_fields=["nalet_pocatek_min", "starty_pocatek", "stav_k"])
    audit_zmena(request, "denik_letadla", "letadlo", letadlo.pk, data.dict())
    return letadla.prehled()


class TerminIn(Schema):
    id: int | None = None
    letadlo_id: int
    nazev: str
    datum: date | None = None
    pri_naletu_h: int | None = None
    poznamka: str = ""


@router.post("/sprava/terminy", response=list[LetadloSpravaOut], summary="Uložit termín")
def sprava_termin(request, data: TerminIn):
    _jen_spravce(request)
    if not data.nazev.strip():
        raise sluzby.ChybaLetu("Zadejte název termínu.")
    if data.datum is None and data.pri_naletu_h is None:
        raise sluzby.ChybaLetu("Zadejte datum nebo celkový nálet, při kterém termín nastane.")
    if data.pri_naletu_h is not None and data.pri_naletu_h < 0:
        raise sluzby.ChybaLetu("Nálet nemůže být záporný.")
    termin = TerminLetadla.objects.filter(pk=data.id).first() if data.id else TerminLetadla()
    if termin is None:
        raise sluzby.ChybaLetu("Termín neexistuje.", status=404)
    termin.letadlo_id = data.letadlo_id
    termin.nazev = data.nazev.strip()[:80]
    termin.datum = data.datum
    termin.pri_naletu_h = data.pri_naletu_h
    termin.poznamka = data.poznamka.strip()[:200]
    termin.save()
    audit_zmena(request, "termin_letadla", "letadlo", data.letadlo_id, data.dict())
    return letadla.prehled()


@router.post("/sprava/terminy/{termin_id}/smazat", response=list[LetadloSpravaOut])
def sprava_termin_smazat(request, termin_id: int):
    _jen_spravce(request)
    termin = TerminLetadla.objects.filter(pk=termin_id).first()
    if termin:
        termin.delete()
        audit_zmena(request, "termin_smazan", "letadlo", termin.letadlo_id, {"nazev": termin.nazev})
    return letadla.prehled()


def audit_zmena(request, akce: str, objekt: str, objekt_id: int, zmeny: dict):
    audit.zapsat(request.user, akce, objekt, objekt_id, zmeny={k: str(v) for k, v in zmeny.items()})
