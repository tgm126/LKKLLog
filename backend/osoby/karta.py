"""Karta osoby: seznam osob a úprava všeho o osobě na jednom místě (admin, správce).

Doklady, provozní oprávnění, přeškolení a výcvik se vybírají z číselníků. Role v aplikaci
mění jen admin. Telefon se posílá jen na vyžádání (samostatné volání).
"""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from ciselniky.models import (
    DruhPrukazu,
    KvalifikacePrukazu,
    ProvozniOpravneni,
    SkupinaPrukazu,
    TypLetadla,
)
from lety import audit, rozletanost

from . import telefon
from .models import KvalifikaceOsoby, Osoba, Preskoleni, PrukazOsoby, Vycvik, smi_spravovat_licence

router = Router(tags=["osoby"], auth=django_auth)

PORADI_STAVU = [rozletanost.OK, rozletanost.INFO, rozletanost.POZOR, rozletanost.CHYBA]


def _jen_spravce(request):
    if not smi_spravovat_licence(request.user):
        raise HttpError(403, "Osoby spravuje admin nebo správce licencí a letadel.")


# --- seznam --------------------------------------------------------------------------------


class RadekOsobyOut(Schema):
    id: int
    jmeno: str
    email: str | None
    aktivni: bool
    externi: bool
    testovaci: bool
    role: list[str]
    prukazy: list[str]
    stav: str
    problemy: list[str]


def _role(o: Osoba) -> list[str]:
    return [
        nazev
        for nazev, ma in (
            ("admin", o.is_staff),
            ("časoměřič", o.role_casomeric),
            ("účetní", o.role_ucetni),
            ("správce", o.role_spravce),
        )
        if ma
    ]


@router.get("", response=list[RadekOsobyOut], summary="Seznam osob se stavem dokladů")
def seznam(request):
    _jen_spravce(request)
    osoby = Osoba.objects.order_by("prijmeni", "jmeno").prefetch_related(
        Prefetch("prukazy", queryset=PrukazOsoby.objects.select_related("druh")),
        Prefetch("vycviky", queryset=Vycvik.objects.select_related("druh")),
    )
    vysledek = []
    for o in osoby:
        piloti = [
            p.druh.nazev
            for p in o.prukazy.all()
            if p.druh.skupina
            in (SkupinaPrukazu.PILOTNI, SkupinaPrukazu.INSTRUKTOR, SkupinaPrukazu.EXAMINATOR)
        ]
        piloti += [f"žák {v.druh.nazev}" for v in o.vycviky.all() if v.ukoncen is None]
        # Stav dokladů má smysl jen u lidí, kteří létají (průkaz nebo výcvik).
        kontroly = rozletanost.kontroly(o) if o.prukazy.all() or o.vycviky.all() else []
        problemy = [
            f"{k.nazev}: {k.text}"
            for k in kontroly
            if k.stav in (rozletanost.POZOR, rozletanost.CHYBA)
        ]
        vysledek.append(
            {
                "id": o.pk,
                "jmeno": f"{o.prijmeni} {o.jmeno}".strip(),
                "email": o.email,
                "aktivni": o.is_active,
                "externi": o.externi,
                "testovaci": o.testovaci,
                "role": _role(o),
                "prukazy": piloti,
                "stav": max((k.stav for k in kontroly), key=PORADI_STAVU.index) if kontroly else "",
                "problemy": problemy,
            }
        )
    return vysledek


# --- volby z číselníků ------------------------------------------------------------------


class VolbaKvalifikaceOut(Schema):
    id: int
    nazev: str
    ma_platnost: bool
    aktivni: bool


class VolbaDruhuOut(Schema):
    id: int
    nazev: str
    skupina: str
    aktivni: bool
    kvalifikace: list[VolbaKvalifikaceOut]


class VolbaOut(Schema):
    id: int
    nazev: str
    aktivni: bool


class VolbaTypuOut(Schema):
    id: int
    nazev: str
    kategorie: str
    aktivni: bool


class VolbyOut(Schema):
    druhy: list[VolbaDruhuOut]
    provozni: list[VolbaOut]
    typy: list[VolbaTypuOut]


@router.get("/volby", response=VolbyOut, summary="Číselníky pro kartu osoby")
def volby(request):
    _jen_spravce(request)
    druhy = DruhPrukazu.objects.prefetch_related(
        Prefetch("kvalifikace", queryset=KvalifikacePrukazu.objects.order_by("poradi", "nazev"))
    )
    return {
        "druhy": [
            {
                "id": d.pk,
                "nazev": d.nazev,
                "skupina": d.skupina,
                "aktivni": d.aktivni,
                "kvalifikace": list(d.kvalifikace.all()),
            }
            for d in druhy
        ],
        "provozni": list(ProvozniOpravneni.objects.all()),
        "typy": list(TypLetadla.objects.order_by("kategorie", "poradi", "nazev")),
    }


# --- karta ---------------------------------------------------------------------------------


class KvalifikaceIO(Schema):
    kvalifikace_id: int
    platnost_do: date | None = None


class PrukazIO(Schema):
    druh_id: int
    cislo: str = ""
    poznamka: str = ""
    kvalifikace: list[KvalifikaceIO] = []


class VycvikIO(Schema):
    druh_id: int
    zahajen: date | None = None
    solo_povoleno: date | None = None
    ukoncen: date | None = None
    poznamka: str = ""


class RoleIO(Schema):
    casomeric: bool = False
    ucetni: bool = False
    spravce: bool = False
    admin: bool = False


class KontrolaOut(Schema):
    oblast: str
    nazev: str
    stav: str
    text: str
    plati_do: date | None
    podrobnosti: list[str]
    modul: str


class KartaOut(Schema):
    id: int
    jmeno: str
    prijmeni: str
    email: str | None
    ma_telefon: bool
    aktivni: bool
    externi: bool
    testovaci: bool
    role: RoleIO
    prukazy: list[PrukazIO]
    provozni: list[int]
    preskoleni: list[int]
    vycviky: list[VycvikIO]
    kontroly: list[KontrolaOut]


class KartaIn(Schema):
    jmeno: str
    prijmeni: str
    email: str | None = None
    telefon: str | None = None  # None = neměnit (telefon se načítá jen na vyžádání)
    aktivni: bool = True
    externi: bool = False
    testovaci: bool = False
    role: RoleIO = RoleIO()
    prukazy: list[PrukazIO] = []
    provozni: list[int] = []
    preskoleni: list[int] = []
    vycviky: list[VycvikIO] = []


def _karta(o: Osoba) -> dict:
    prukazy = (
        PrukazOsoby.objects.filter(osoba=o)
        .select_related("druh")
        .prefetch_related("kvalifikace")
        .order_by("druh__poradi")
    )
    return {
        "id": o.pk,
        "jmeno": o.jmeno,
        "prijmeni": o.prijmeni,
        "email": o.email,
        "ma_telefon": bool(o.telefon),
        "aktivni": o.is_active,
        "externi": o.externi,
        "testovaci": o.testovaci,
        "role": {
            "casomeric": o.role_casomeric,
            "ucetni": o.role_ucetni,
            "spravce": o.role_spravce,
            "admin": o.is_staff,
        },
        "prukazy": [
            {
                "druh_id": p.druh_id,
                "cislo": p.cislo,
                "poznamka": p.poznamka,
                "kvalifikace": [
                    {"kvalifikace_id": k.kvalifikace_id, "platnost_do": k.platnost_do}
                    for k in p.kvalifikace.all()
                ],
            }
            for p in prukazy
        ],
        "provozni": list(o.provozni_opravneni.values_list("pk", flat=True)),
        "preskoleni": list(o.preskoleni.values_list("typ_id", flat=True)),
        "vycviky": list(o.vycviky.order_by("-zahajen", "pk").values()),
        "kontroly": rozletanost.kontroly(o),
    }


def _osoba(osoba_id: int) -> Osoba:
    osoba = Osoba.objects.filter(pk=osoba_id).first()
    if osoba is None:
        raise HttpError(404, "Osoba neexistuje.")
    return osoba


@router.get("/{osoba_id}", response=KartaOut, summary="Karta osoby")
def karta(request, osoba_id: int):
    _jen_spravce(request)
    return _karta(_osoba(osoba_id))


class TelefonOut(Schema):
    telefon: str


@router.get("/{osoba_id}/telefon", response=TelefonOut, summary="Telefon (jen na vyžádání)")
def telefon_osoby(request, osoba_id: int):
    _jen_spravce(request)
    return {"telefon": _osoba(osoba_id).telefon}


def _ulozit(request, osoba: Osoba | None, data: KartaIn) -> Osoba:
    admin = request.user.is_staff
    if not data.jmeno.strip() or not data.prijmeni.strip():
        raise HttpError(400, "Zadejte jméno a příjmení.")
    druhy = [p.druh_id for p in data.prukazy]
    if len(set(druhy)) != len(druhy):
        raise HttpError(400, "Každý druh průkazu jen jednou.")
    kvalifikace = {
        k.pk: k
        for k in KvalifikacePrukazu.objects.filter(
            pk__in=[k.kvalifikace_id for p in data.prukazy for k in p.kvalifikace]
        )
    }
    for p in data.prukazy:
        for k in p.kvalifikace:
            if k.kvalifikace_id not in kvalifikace or kvalifikace[k.kvalifikace_id].druh_id != (
                p.druh_id
            ):
                raise HttpError(400, "Kvalifikace k tomuto průkazu nepatří.")

    novy = osoba is None
    if novy:
        osoba = Osoba(email=None)
        osoba.set_unusable_password()
    osoba.jmeno = data.jmeno.strip()
    osoba.prijmeni = data.prijmeni.strip()
    osoba.email = (data.email or "").strip().lower() or None
    if data.telefon is not None:
        osoba.telefon = telefon.normalizovat(data.telefon)
    osoba.is_active = data.aktivni
    osoba.externi = data.externi
    osoba.testovaci = data.testovaci
    if admin:  # role mění jen admin
        osoba.role_casomeric = data.role.casomeric
        osoba.role_ucetni = data.role.ucetni
        osoba.role_spravce = data.role.spravce
        if osoba.pk != request.user.pk:  # sám sobě admina neodebere
            osoba.is_staff = data.role.admin
    try:
        osoba.full_clean(exclude=["password"])
        with transaction.atomic():
            osoba.save()
            PrukazOsoby.objects.filter(osoba=osoba).exclude(druh_id__in=druhy).delete()
            for p in data.prukazy:
                prukaz, _ = PrukazOsoby.objects.update_or_create(
                    osoba=osoba,
                    druh_id=p.druh_id,
                    defaults={"cislo": p.cislo.strip()[:40], "poznamka": p.poznamka.strip()[:200]},
                )
                prukaz.kvalifikace.all().delete()
                KvalifikaceOsoby.objects.bulk_create(
                    [
                        KvalifikaceOsoby(
                            prukaz=prukaz,
                            kvalifikace_id=k.kvalifikace_id,
                            platnost_do=k.platnost_do,
                        )
                        for k in p.kvalifikace
                    ]
                )
            osoba.provozni_opravneni.set(data.provozni)
            osoba.preskoleni.exclude(typ_id__in=data.preskoleni).delete()
            for typ_id in data.preskoleni:
                Preskoleni.objects.get_or_create(osoba=osoba, typ_id=typ_id)
            osoba.vycviky.all().delete()
            Vycvik.objects.bulk_create([Vycvik(osoba=osoba, **v.dict()) for v in data.vycviky])
    except ValidationError as e:
        zpravy = " ".join(m for seznam in e.message_dict.values() for m in seznam)
        raise HttpError(400, zpravy) from e
    except IntegrityError as e:
        raise HttpError(400, "Údaje se nedají uložit (e-mail už má jiná osoba?).") from e
    audit.zapsat(
        request.user,
        "karta_osoby_nova" if novy else "karta_osoby",
        "osoba",
        osoba.pk,
        zmeny={
            "prukazy": [
                [p.druh_id, [[k.kvalifikace_id, str(k.platnost_do or "")] for k in p.kvalifikace]]
                for p in data.prukazy
            ],
            "provozni": data.provozni,
            "preskoleni": data.preskoleni,
        },
    )
    return osoba


@router.post("", response=KartaOut, summary="Nová osoba")
def nova(request, data: KartaIn):
    _jen_spravce(request)
    return _karta(_ulozit(request, None, data))


@router.post("/{osoba_id}", response=KartaOut, summary="Uložit kartu osoby")
def ulozit(request, osoba_id: int, data: KartaIn):
    _jen_spravce(request)
    return _karta(_ulozit(request, _osoba(osoba_id), data))
