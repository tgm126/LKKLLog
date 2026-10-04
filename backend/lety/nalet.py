"""Můj nálet (kap. 4.8 návrhu): neoficiální osobní součty hodin a startů.

Počítají se ukončené lety, na kterých byl člověk PIC, žák nebo přezkoušený – včetně
soukromých letadel (jde o osobní nálet, ne o účetnictví). Zrušené lety ne.
"""

import io
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date

from django.db.models import QuerySet
from django.utils import timezone
from openpyxl import Workbook

from osoby.models import Kategorie, Osoba

from .models import FunkcePosadky, Let, Posadka, StavLetu, Ucel, ZpusobVzletu
from .obdobi import rozsah
from .sluzby import ChybaLetu
from .vypis import _list, letecky

FUNKCE_NALETU = (FunkcePosadky.PIC, FunkcePosadky.ZAK, FunkcePosadky.PREZKOUSENY)
MAX_DNU = 3700  # i celý zápisník za deset let


@dataclass
class MujLet:
    let: Let
    funkce: str


def lety(osoba: Osoba, od: date, do: date, zaklad: QuerySet) -> list[MujLet]:
    """Vlastní lety v období; `zaklad` je dotaz na lety s přednačtenými údaji (API)."""
    if do < od:
        raise ChybaLetu("Konec období je před začátkem.")
    if (do - od).days > MAX_DNU:
        raise ChybaLetu("Období je příliš dlouhé.")
    zacatek, konec = rozsah(od, do)
    funkce = dict(
        Posadka.objects.filter(
            osoba=osoba,
            funkce__in=FUNKCE_NALETU,
            let__stav=StavLetu.UKONCEN,
            let__cas_vzletu__gte=zacatek,
            let__cas_vzletu__lt=konec,
        ).values_list("let_id", "funkce")
    )
    seznam = zaklad.filter(pk__in=funkce).order_by("cas_vzletu", "id")
    return [MujLet(let, funkce[let.pk]) for let in seznam]


def souhrn(seznam: list[MujLet]) -> dict:
    kategorie = dict(Kategorie.choices)
    funkce = dict(FunkcePosadky.choices)
    ucel = dict(Ucel.choices)
    zpusob = dict(ZpusobVzletu.choices)

    def nove():
        return {"lety": 0, "minuty": 0, "pristani": 0}

    def pricti(radek, m: MujLet):
        radek["lety"] += 1
        radek["minuty"] += m.let.doba_uctovana_min or 0
        radek["pristani"] += m.let.pocet_pristani

    celkem = nove()
    podle_kategorie: dict[tuple, dict] = defaultdict(nove)
    podle_ucelu: dict[str, dict] = defaultdict(nove)
    starty: dict[tuple, int] = defaultdict(int)
    poradi_kat = list(kategorie)
    poradi_fun = list(FUNKCE_NALETU)
    for m in seznam:
        kat = m.let.letadlo.kategorie
        pricti(celkem, m)
        pricti(podle_kategorie[(poradi_kat.index(kat), poradi_fun.index(m.funkce))], m)
        pricti(podle_ucelu[m.let.ucel], m)
        starty[(poradi_kat.index(kat), m.let.zpusob_vzletu)] += 1
    return {
        "celkem": celkem,
        "podle_kategorie": [
            {
                "kategorie": kategorie[poradi_kat[k]],
                "funkce": funkce[poradi_fun[f]],
                **v,
            }
            for (k, f), v in sorted(podle_kategorie.items())
        ],
        "podle_ucelu": [
            {"ucel": ucel[u], **v}
            for u, v in sorted(podle_ucelu.items(), key=lambda x: -x[1]["minuty"])
        ],
        "starty": [
            {"kategorie": kategorie[poradi_kat[k]], "zpusob": zpusob[z], "pocet": n}
            for (k, z), n in sorted(starty.items())
        ],
    }


def excel(osoba: Osoba, seznam: list[MujLet], od: date, do: date) -> bytes:
    """Vlastní lety do Excelu – podklad pro zápisník letů."""
    s = souhrn(seznam)
    kategorie = dict(Kategorie.choices)
    funkce = dict(FunkcePosadky.choices)
    ucel = dict(Ucel.choices)
    zpusob = dict(ZpusobVzletu.choices)
    cas = lambda d: d.astimezone(UTC).strftime("%H:%M") if d else ""  # noqa: E731

    wb = Workbook()
    wb.remove(wb.active)
    radky = []
    for m in seznam:
        let = m.let
        ostatni = ", ".join(
            f"{p.osoba.get_full_name()} ({funkce[p.funkce]})"
            for p in let.posadka.all()
            if p.osoba_id != osoba.pk
        )
        radky.append(
            [
                let.cas_vzletu.astimezone(UTC).date(),
                let.letadlo.imatrikulace,
                let.letadlo.typ,
                kategorie[let.letadlo.kategorie],
                funkce[m.funkce],
                ucel[let.ucel],
                str(let.uloha) if let.uloha else "",
                zpusob[let.zpusob_vzletu],
                str(let.misto_vzletu),
                cas(let.cas_vzletu),
                str(let.misto_pristani) if let.misto_pristani else "",
                cas(let.cas_pristani),
                let.doba_uctovana_min,
                letecky(let.doba_uctovana_min),
                let.pocet_pristani,
                ostatni,
            ]
        )
    ws = _list(
        wb,
        "Lety",
        [
            "Datum",
            "Letadlo",
            "Typ",
            "Kategorie",
            "Funkce",
            "Účel",
            "Úloha",
            "Způsob vzletu",
            "Místo vzletu",
            "Vzlet UTC",
            "Místo přistání",
            "Přistání UTC",
            "Doba [min]",
            "Doba",
            "Přistání",
            "Další posádka",
        ],
        radky,
    )
    for bunka in ws["A"][1:]:
        bunka.number_format = "DD.MM.YYYY"

    def hodnoty(r):
        return [r["lety"], r["minuty"], letecky(r["minuty"]), r["pristani"]]

    _list(
        wb,
        "Souhrn",
        ["Kategorie", "Funkce", "Lety", "Minuty", "Doba", "Přistání"],
        [[r["kategorie"], r["funkce"], *hodnoty(r)] for r in s["podle_kategorie"]]
        + [["Celkem", "", *hodnoty(s["celkem"])]],
    )
    _list(
        wb,
        "Parametry",
        ["Parametr", "Hodnota"],
        [
            ["Pilot", osoba.get_full_name()],
            ["Období (UTC)", f"{od:%d.%m.%Y} – {do:%d.%m.%Y}"],
            ["Vytvořeno (UTC)", timezone.now().astimezone(UTC).strftime("%d.%m.%Y %H:%M")],
            ["Počítají se", "ukončené lety ve funkci PIC, žák, přezkoušený, i soukromá letadla"],
            ["Upozornění", "Neoficiální přehled z evidence aeroklubu, nenahrazuje zápisník letů."],
        ],
    )
    vystup = io.BytesIO()
    wb.save(vystup)
    return vystup.getvalue()
