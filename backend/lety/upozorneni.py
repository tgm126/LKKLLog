"""Upozornění na neukončené lety (etapa 10): e-mailem a push notifikací.

Kontrolu spouští cron serveru každých 5 minut přes den (server/udrzba.sh). Každý druh
upozornění dostane let nejvýš jednou. Dostanou ho lidé, kteří s letem něco udělat
můžou: kdo let založil a PIC, žák nebo přezkoušený (ne externí osoby).
"""

import logging
from datetime import UTC, datetime, time, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from osoby.models import Osoba
from provoz import email, push

from . import audit
from .models import FunkcePosadky, Let, StavLetu, Upozorneni
from .obdobi import den_letu
from .slunce import slunce
from .vypis import letecky

log = logging.getLogger(__name__)
Druh = Upozorneni.Druh


def prijemci(let: Let) -> list[Osoba]:
    ids = {let.zalozil_id} | {
        p.osoba_id
        for p in let.posadka.all()
        if p.funkce in (FunkcePosadky.PIC, FunkcePosadky.ZAK, FunkcePosadky.PREZKOUSENY)
    }
    return list(Osoba.objects.filter(pk__in=ids, is_active=True, externi=False))


def _hhmm(cas: datetime) -> str:
    return cas.astimezone(UTC).strftime("%H:%M")


def _zprava(let: Let, druh: str, ted: datetime) -> tuple[str, str]:
    """Titulek a text upozornění."""
    imatrikulace = let.letadlo.imatrikulace
    kdo = next((p.osoba.get_full_name() for p in let.posadka.all() if p.funkce == "pic"), "")
    if druh == Druh.MAX_DOBA:
        doba = int((ted - let.cas_vzletu).total_seconds() // 60)
        return (
            f"{imatrikulace}: déle než max. doba letu",
            f"{imatrikulace} ({kdo}) je ve vzduchu {letecky(doba)} od {_hhmm(let.cas_vzletu)} "
            f"UTC, maximální doba je {letecky(let.letadlo.max_doba_min)}. "
            "Pokud už přistál, zapište přistání.",
        )
    if druh == Druh.SOUMRAK:
        soumrak = slunce(den_letu(let))["soumrak"]
        return (
            f"{imatrikulace}: ve vzduchu po soumraku",
            f"Soumrak skončil v {_hhmm(soumrak)} UTC a let {imatrikulace} ({kdo}) "
            f"od {_hhmm(let.cas_vzletu)} UTC stále není ukončený. "
            "Pokud už přistál, zapište přistání.",
        )
    den = den_letu(let) or let.zalozeno.astimezone(UTC).date()
    stav = "je stále ve vzduchu" if let.stav == StavLetu.VE_VZDUCHU else "zůstal připravený"
    return (
        f"{imatrikulace}: neukončený let z {den.day}. {den.month}.",
        f"Let {imatrikulace} ({kdo}) ze dne {den.day}. {den.month}. {stav}, "
        "takže den nejde uzavřít. Zapište přistání, nebo let zrušte.",
    )


def upozornit(let: Let, druh: str, ted: datetime | None = None) -> Upozorneni | None:
    """Pošle upozornění, pokud tento druh pro let ještě neodešel."""
    ted = ted or timezone.now()
    try:
        with transaction.atomic():
            zaznam = Upozorneni.objects.create(let=let, druh=druh)
    except IntegrityError:
        return None  # už odešlo (nebo ho právě posílá souběžná kontrola)

    titulek, text = _zprava(let, druh, ted)
    predmet, telo = f"LKKL Log – {titulek}", f"{text}\n\n{settings.APP_URL}/"
    e_maily = pushe = 0
    for osoba in prijemci(let):
        if osoba.email and email.odeslat(osoba.email, predmet, telo):
            e_maily += 1
        pushe += push.poslat(osoba, titulek, text, url="/", znacka=f"let-{let.pk}-{druh}")
    zaznam.prijemci = {"e-maily": e_maily, "push": pushe}
    zaznam.save(update_fields=["prijemci"])
    audit.zapsat(
        None,
        "upozorneni",
        "let",
        let.pk,
        zmeny={"druh": druh, **zaznam.prijemci},
        duvod=Druh(druh).label,
    )
    return zaznam


def kontrola(ted: datetime | None = None) -> list[Upozorneni]:
    """Najde neukončené lety a pošle k nim upozornění."""
    ted = ted or timezone.now()
    dnes = datetime.combine(ted.astimezone(UTC).date(), time.min, tzinfo=UTC)
    odeslana = []
    lety = (
        Let.objects.select_related("letadlo")
        .prefetch_related("posadka__osoba")
        .filter(
            # Za posledních 31 dní – starší zapomenuté lety už upozornění nespraví.
            Q(stav=StavLetu.VE_VZDUCHU, cas_vzletu__gte=dnes - timedelta(31))
            # Připravené lety z minulých dnů.
            | Q(stav=StavLetu.PRIPRAVEN, zalozeno__lt=dnes, zalozeno__gte=dnes - timedelta(31))
        )
    )
    for let in lety:
        druhy = []
        if let.stav == StavLetu.VE_VZDUCHU:
            max_doba = let.letadlo.max_doba_min
            if max_doba and ted - let.cas_vzletu > timedelta(minutes=max_doba):
                druhy.append(Druh.MAX_DOBA)
            if ted > slunce(den_letu(let))["soumrak"]:
                druhy.append(Druh.SOUMRAK)
            if let.cas_vzletu < dnes:
                druhy.append(Druh.NEUKONCENY)
        else:
            druhy.append(Druh.NEUKONCENY)
        for druh in druhy:
            if zaznam := upozornit(let, druh, ted):
                odeslana.append(zaznam)
    return odeslana
