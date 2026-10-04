"""Správa číselníků (jen admin). Jedno obecné API pro všechny číselníky podle popisu polí."""

from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from lety import audit
from lety.models import Letiste, Osnova, Ucel, Uloha
from osoby.models import Kategorie

from .models import (
    DruhPrukazu,
    DruhTerminu,
    KvalifikacePrukazu,
    ProvozniOpravneni,
    SkupinaPrukazu,
    TypLetadla,
)

router = Router(tags=["číselníky"], auth=django_auth)


@dataclass
class Pole:
    klic: str
    nazev: str
    typ: str = "text"  # text | cislo | bool | volba | vice
    volby: list = field(default_factory=list)  # (hodnota, název)


@dataclass
class Ciselnik:
    klic: str
    nazev: str
    model: type
    pole: list[Pole]
    popis: str = ""
    rodic: str | None = None  # pole s odkazem na nadřazenou položku (hierarchie)
    deti: str | None = None  # klíč podřízeného číselníku


AKTIVNI = Pole("aktivni", "Aktivní", "bool")
PORADI = Pole("poradi", "Pořadí", "cislo")
KATEGORIE = Pole("kategorie", "Kategorie", "volba", list(Kategorie.choices))
KATEGORIE_VICE = Pole("kategorie", "Kategorie letadel", "vice", list(Kategorie.choices))

CISELNIKY = {
    c.klic: c
    for c in [
        Ciselnik(
            "typy-letadel",
            "Typy letadel",
            TypLetadla,
            [Pole("nazev", "Název"), KATEGORIE, AKTIVNI, PORADI],
            "Na typ se přeškolují piloti; letadlo z něj přebírá kategorii.",
        ),
        Ciselnik(
            "druhy-prukazu",
            "Druhy průkazů",
            DruhPrukazu,
            [
                Pole("nazev", "Název"),
                Pole("skupina", "Skupina", "volba", list(SkupinaPrukazu.choices)),
                KATEGORIE_VICE,
                AKTIVNI,
                PORADI,
            ],
            "Průkazy a doklady osob; pod každým jsou jeho kvalifikace.",
            deti="kvalifikace",
        ),
        Ciselnik(
            "kvalifikace",
            "Kvalifikace",
            KvalifikacePrukazu,
            [
                Pole("nazev", "Název"),
                Pole("ma_platnost", "Má platnost", "bool"),
                KATEGORIE_VICE,
                AKTIVNI,
                PORADI,
            ],
            rodic="druh",
        ),
        Ciselnik(
            "provozni-opravneni",
            "Provozní oprávnění",
            ProvozniOpravneni,
            [Pole("nazev", "Název"), AKTIVNI, PORADI],
            "Činnosti v provozu, ke kterým je člověk způsobilý.",
        ),
        Ciselnik(
            "druhy-terminu",
            "Druhy termínů letadel",
            DruhTerminu,
            [Pole("nazev", "Název"), AKTIVNI, PORADI],
        ),
        Ciselnik(
            "letiste",
            "Letiště",
            Letiste,
            [
                Pole("icao", "ICAO"),
                Pole("nazev", "Název"),
                Pole("domovske", "Domovské", "bool"),
                Pole("teren", "Mimo letiště", "bool"),
                AKTIVNI,
                PORADI,
            ],
        ),
        Ciselnik(
            "osnovy",
            "Osnovy",
            Osnova,
            [KATEGORIE, Pole("nazev", "Název"), AKTIVNI, PORADI],
            "Výcvikové osnovy; pod každou jsou její úlohy.",
            deti="ulohy",
        ),
        Ciselnik(
            "ulohy",
            "Úlohy",
            Uloha,
            [
                Pole("kod", "Kód"),
                Pole("nazev", "Název"),
                Pole("ucely", "Účely", "vice", list(Ucel.choices)),
                AKTIVNI,
                PORADI,
            ],
            rodic="osnova",
        ),
    ]
}


def _jen_admin(request):
    if not request.user.is_staff:
        raise HttpError(403, "Číselníky spravuje admin.")


def _ciselnik(klic: str) -> Ciselnik:
    if klic not in CISELNIKY:
        raise HttpError(404, "Neznámý číselník.")
    return CISELNIKY[klic]


class PoleOut(Schema):
    klic: str
    nazev: str
    typ: str
    volby: list[list[str]]


class RadekOut(Schema):
    id: int
    systemova: bool
    hodnoty: dict


class CiselnikOut(Schema):
    klic: str
    nazev: str
    popis: str
    deti: str | None
    pole: list[PoleOut]
    radky: list[RadekOut]


class PrehledOut(Schema):
    klic: str
    nazev: str
    popis: str
    rodic: bool
    deti: str | None
    pocet: int


@router.get("", response=list[PrehledOut], summary="Seznam číselníků")
def seznam(request):
    _jen_admin(request)
    return [
        {
            "klic": c.klic,
            "nazev": c.nazev,
            "popis": c.popis,
            "rodic": c.rodic is not None,
            "deti": c.deti,
            "pocet": c.model.objects.count(),
        }
        for c in CISELNIKY.values()
    ]


def _radky(c: Ciselnik, rodic: int | None) -> dict:
    dotaz = c.model.objects.all()
    if c.rodic:
        dotaz = dotaz.filter(**{f"{c.rodic}_id": rodic})
    radky = [
        {
            "id": obj.pk,
            "systemova": bool(getattr(obj, "systemova", False)),
            "hodnoty": {p.klic: getattr(obj, p.klic) for p in c.pole},
        }
        for obj in dotaz.order_by("poradi", "pk")
    ]
    return {
        "klic": c.klic,
        "nazev": c.nazev,
        "popis": c.popis,
        "deti": c.deti,
        "pole": [
            {"klic": p.klic, "nazev": p.nazev, "typ": p.typ, "volby": [list(v) for v in p.volby]}
            for p in c.pole
        ],
        "radky": radky,
    }


@router.get("/{klic}", response=CiselnikOut, summary="Položky číselníku")
def polozky(request, klic: str, rodic: int | None = None):
    _jen_admin(request)
    return _radky(_ciselnik(klic), rodic)


class UlozitIn(Schema):
    id: int | None = None
    rodic: int | None = None
    hodnoty: dict


def _hodnota(pole: Pole, hodnota):
    if pole.typ == "bool":
        return bool(hodnota)
    if pole.typ == "cislo":
        return int(hodnota or 0)
    if pole.typ == "vice":
        povolene = {v for v, _ in pole.volby}
        hodnoty = list(hodnota or [])
        if any(h not in povolene for h in hodnoty):
            raise HttpError(400, f"{pole.nazev}: neznámá hodnota.")
        return hodnoty
    if pole.typ == "volba":
        if hodnota not in {v for v, _ in pole.volby}:
            raise HttpError(400, f"{pole.nazev}: vyberte hodnotu.")
        return hodnota
    text = str(hodnota or "").strip()
    return text or None if pole.klic == "icao" else text


@router.post("/{klic}", response=CiselnikOut, summary="Uložit položku")
def ulozit(request, klic: str, data: UlozitIn):
    _jen_admin(request)
    c = _ciselnik(klic)
    obj = c.model.objects.filter(pk=data.id).first() if data.id else c.model()
    if obj is None:
        raise HttpError(404, "Položka neexistuje.")
    if c.rodic and not data.id:
        if data.rodic is None:
            raise HttpError(400, "Chybí nadřazená položka.")
        setattr(obj, f"{c.rodic}_id", data.rodic)
    for p in c.pole:
        if p.klic in data.hodnoty:
            setattr(obj, p.klic, _hodnota(p, data.hodnoty[p.klic]))
    try:
        obj.full_clean()
        with transaction.atomic():
            obj.save()
    except ValidationError as e:
        zpravy = " ".join(m for seznam in e.message_dict.values() for m in seznam)
        raise HttpError(400, zpravy) from e
    except IntegrityError as e:
        raise HttpError(400, "Taková položka už v číselníku je.") from e
    audit.zapsat(
        request.user,
        "ciselnik",
        klic,
        obj.pk,
        zmeny={p.klic: str(getattr(obj, p.klic)) for p in c.pole},
    )
    return _radky(c, getattr(obj, f"{c.rodic}_id") if c.rodic else None)


@router.post("/{klic}/{polozka_id}/smazat", response=CiselnikOut, summary="Smazat položku")
def smazat(request, klic: str, polozka_id: int):
    _jen_admin(request)
    c = _ciselnik(klic)
    obj = c.model.objects.filter(pk=polozka_id).first()
    if obj is None:
        raise HttpError(404, "Položka neexistuje.")
    if getattr(obj, "systemova", False):
        raise HttpError(400, "Systémovou hodnotu nejde smazat – můžete ji deaktivovat.")
    rodic = getattr(obj, f"{c.rodic}_id") if c.rodic else None
    try:
        with transaction.atomic():
            obj.delete()
    except ProtectedError as e:
        raise HttpError(400, "Hodnota se používá – deaktivujte ji místo smazání.") from e
    audit.zapsat(request.user, "ciselnik_smazano", klic, polozka_id, zmeny={"nazev": str(obj)})
    return _radky(c, rodic)
