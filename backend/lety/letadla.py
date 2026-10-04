"""Nálet letadel a jejich termíny (ARC, prohlídky…) pro přehled správce.

Celkový nálet = stav z provozního deníku k zadanému dni + lety z evidence po něm.
U letadel se počítá skutečná doba letu (i „start bez doby“ se počítá jako start).
"""

from datetime import UTC, date

from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from .models import Letadlo, StavLetu, TerminLetadla
from .rozletanost import CHYBA, OK, POZOR, datum
from .vypis import letecky

BRZY_DNY = 30
BRZY_HODIN = 10


def s_naletem():
    """Letadla s celkovým náletem (minuty) a starty."""
    # Lety po dni stavu deníku (datum vzletu v UTC); bez stavu deníku všechny.
    po_stavu = Q(lety__stav=StavLetu.UKONCEN) & (
        Q(stav_k__isnull=True) | Q(lety__cas_vzletu__date__gt=F("stav_k"))
    )
    return Letadlo.objects.annotate(
        nalet_evidence=Sum("lety__doba_min", filter=po_stavu),
        starty_evidence=Count("lety", filter=po_stavu),
    )


def nalet_min(letadlo) -> int:
    return letadlo.nalet_pocatek_min + (letadlo.nalet_evidence or 0)


def starty(letadlo) -> int:
    return letadlo.starty_pocatek + (letadlo.starty_evidence or 0)


def stav_terminu(termin: TerminLetadla, nalet: int, dnes: date) -> tuple[str, str]:
    """Stav a popis termínu; rozhoduje, co nastane dřív (datum, nebo nálet)."""
    stavy, popisy = [], []
    if termin.datum:
        dni = (termin.datum - dnes).days
        if dni < 0:
            stavy.append(CHYBA)
            popisy.append(f"prošlo {datum(termin.datum)}")
        else:
            stavy.append(POZOR if dni <= BRZY_DNY else OK)
            popisy.append(f"do {datum(termin.datum)} (za {dni} dní)")
    if termin.pri_naletu_h is not None:
        zbyva = termin.pri_naletu_h * 60 - nalet
        if zbyva <= 0:
            stavy.append(CHYBA)
            popisy.append(f"při {termin.pri_naletu_h} h – překročeno o {letecky(-zbyva)}")
        else:
            stavy.append(POZOR if zbyva <= BRZY_HODIN * 60 else OK)
            popisy.append(f"při {termin.pri_naletu_h} h – zbývá {letecky(zbyva)}")
    poradi = [OK, POZOR, CHYBA]
    return max(stavy, key=poradi.index), ", ".join(popisy)


def prehled(dnes: date | None = None) -> list[dict]:
    dnes = dnes or timezone.now().astimezone(UTC).date()
    vysledek = []
    letadla = (
        s_naletem()
        .filter(aktivni=True)
        .prefetch_related("terminy")
        .order_by("poradi", "imatrikulace")
    )
    for letadlo in letadla:
        nalet = nalet_min(letadlo)
        terminy = []
        for t in letadlo.terminy.all():
            stav, text = stav_terminu(t, nalet, dnes)
            terminy.append(
                {
                    "id": t.pk,
                    "nazev": t.nazev,
                    "datum": t.datum,
                    "pri_naletu_h": t.pri_naletu_h,
                    "poznamka": t.poznamka,
                    "stav": stav,
                    "text": text,
                }
            )
        vysledek.append(
            {
                "id": letadlo.pk,
                "imatrikulace": letadlo.imatrikulace,
                "typ": letadlo.typ,
                "kategorie": letadlo.kategorie,
                "nalet_min": nalet,
                "starty": starty(letadlo),
                "nalet_pocatek_min": letadlo.nalet_pocatek_min,
                "starty_pocatek": letadlo.starty_pocatek,
                "stav_k": letadlo.stav_k,
                # Bez stavu provozního deníku nesedí celkový nálet ani termíny podle náletu.
                "chybi_denik": letadlo.stav_k is None,
                "terminy": terminy,
            }
        )
    return vysledek


def varovani_letadla(letadlo_id: int, dnes: date | None = None) -> list[str]:
    """Prošlé termíny letadla (datum nebo nálet) – pro varování při zakládání letu."""
    dnes = dnes or timezone.now().astimezone(UTC).date()
    letadlo = s_naletem().filter(pk=letadlo_id).prefetch_related("terminy").first()
    if letadlo is None:
        return []
    nalet = nalet_min(letadlo)
    vysledek = []
    for t in letadlo.terminy.all():
        stav, text = stav_terminu(t, nalet, dnes)
        if stav == CHYBA:
            vysledek.append(f"{letadlo.imatrikulace}: {t.nazev} – {text}.")
    return vysledek
