"""Karta letadla: údaje, typ z číselníku, stav provozního deníku a termíny (admin, správce)."""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from ciselniky.models import DruhTerminu, TypLetadla
from osoby.models import smi_spravovat_licence

from . import audit, letadla
from .models import Letadlo, TerminLetadla

router = Router(tags=["letadla"], auth=django_auth)

POLE = (
    "pocet_mist",
    "max_doba_min",
    "vlecne",
    "soukrome",
    "aktivni",
    "poradi",
    "nalet_pocatek_min",
    "starty_pocatek",
    "stav_k",
)


def _jen_spravce(request):
    if not smi_spravovat_licence(request.user):
        raise HttpError(403, "Letadla spravuje admin nebo správce licencí a letadel.")


class TerminIO(Schema):
    druh_id: int
    datum: date | None = None
    pri_naletu_h: int | None = None
    poznamka: str = ""


class TerminOut(TerminIO):
    id: int
    nazev: str
    stav: str
    text: str


class KartaLetadlaOut(Schema):
    id: int
    imatrikulace: str
    typ_letadla_id: int | None
    typ: str
    kategorie: str
    pocet_mist: int
    max_doba_min: int | None
    vlecne: bool
    soukrome: bool
    aktivni: bool
    poradi: int
    nalet_min: int
    starty: int
    nalet_pocatek_min: int
    starty_pocatek: int
    stav_k: date | None
    chybi_denik: bool
    terminy: list[TerminOut]


class KartaLetadlaIn(Schema):
    imatrikulace: str
    typ_letadla_id: int | None = None
    pocet_mist: int = 2
    max_doba_min: int | None = None
    vlecne: bool = False
    soukrome: bool = False
    aktivni: bool = True
    poradi: int = 100
    nalet_pocatek_min: int = 0
    starty_pocatek: int = 0
    stav_k: date | None = None
    terminy: list[TerminIO] = []


class VolbaOut(Schema):
    id: int
    nazev: str
    aktivni: bool


class VolbaTypuOut(VolbaOut):
    kategorie: str


class VolbyLetadelOut(Schema):
    typy: list[VolbaTypuOut]
    druhy_terminu: list[VolbaOut]


@router.get("", response=list[KartaLetadlaOut], summary="Letadla s náletem a termíny")
def seznam(request, vse: bool = False):
    _jen_spravce(request)
    return letadla.prehled(vse=vse)


@router.get("/volby", response=VolbyLetadelOut, summary="Číselníky pro kartu letadla")
def volby(request):
    _jen_spravce(request)
    return {
        "typy": list(TypLetadla.objects.order_by("kategorie", "poradi", "nazev")),
        "druhy_terminu": list(DruhTerminu.objects.all()),
    }


@router.get("/{letadlo_id}", response=KartaLetadlaOut, summary="Karta letadla")
def karta(request, letadlo_id: int):
    _jen_spravce(request)
    data = letadla.jedno(letadlo_id)
    if data is None:
        raise HttpError(404, "Letadlo neexistuje.")
    return data


def _ulozit(request, letadlo: Letadlo | None, data: KartaLetadlaIn) -> int:
    typ = TypLetadla.objects.filter(pk=data.typ_letadla_id).first()
    if typ is None:
        raise HttpError(400, "Vyberte typ letadla.")
    if any(t.datum is None and t.pri_naletu_h is None for t in data.terminy):
        raise HttpError(400, "U každého termínu zadejte datum nebo nálet.")
    if min(data.nalet_pocatek_min, data.starty_pocatek) < 0:
        raise HttpError(400, "Nálet a starty nemohou být záporné.")
    novy = letadlo is None
    letadlo = letadlo or Letadlo()
    letadlo.imatrikulace = data.imatrikulace.strip().upper()
    letadlo.typ_letadla = typ
    letadlo.typ, letadlo.kategorie = typ.nazev, typ.kategorie  # i pro kontroly níže
    for pole in POLE:
        setattr(letadlo, pole, getattr(data, pole))
    try:
        letadlo.full_clean()
        with transaction.atomic():
            letadlo.save()
            letadlo.terminy.all().delete()
            TerminLetadla.objects.bulk_create(
                [TerminLetadla(letadlo=letadlo, **t.dict()) for t in data.terminy]
            )
    except ValidationError as e:
        zpravy = " ".join(m for seznam in e.message_dict.values() for m in seznam)
        raise HttpError(400, zpravy) from e
    except IntegrityError as e:
        raise HttpError(400, "Letadlo se nedá uložit (imatrikulace už existuje?).") from e
    zmeny = {k: str(v) for k, v in data.dict().items() if k != "terminy"}
    zmeny["terminy"] = [[t.druh_id, str(t.datum or ""), t.pri_naletu_h] for t in data.terminy]
    akce = "karta_letadla_nova" if novy else "karta_letadla"
    audit.zapsat(request.user, akce, "letadlo", letadlo.pk, zmeny=zmeny)
    return letadlo.pk


@router.post("", response=KartaLetadlaOut, summary="Nové letadlo")
def nove(request, data: KartaLetadlaIn):
    _jen_spravce(request)
    return letadla.jedno(_ulozit(request, None, data))


@router.post("/{letadlo_id}", response=KartaLetadlaOut, summary="Uložit kartu letadla")
def ulozit(request, letadlo_id: int, data: KartaLetadlaIn):
    _jen_spravce(request)
    letadlo = Letadlo.objects.filter(pk=letadlo_id).first()
    if letadlo is None:
        raise HttpError(404, "Letadlo neexistuje.")
    return letadla.jedno(_ulozit(request, letadlo, data))
