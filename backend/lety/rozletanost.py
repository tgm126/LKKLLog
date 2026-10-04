"""Licence, medical a rozlétanost (etapa 12).

Pravidla a zdroje jsou popsané v docs/licence-a-rozletanost.md. Počítá se jen z letů
zapsaných v LKKL Log – lety jinde aplikace nezná, výsledek je proto orientační.

„Platí do“ = poslední den, kdy je podmínka ještě splněná, když už pilot nepoletí:
od nejnovějších letů se sčítá, dokud není podmínka splněná, a k datu letu, který ji
doplnil, se přičte lhůta (90 dní nebo 24 měsíců).
"""

import calendar
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, timedelta

from django.utils import timezone

from osoby.models import (
    MEDICAL_LICENCE,
    DruhKvalifikace,
    Kategorie,
    Licence,
    Medical,
    Opravneni,
    Osoba,
    TridaMedicalu,
    TypLicence,
    Uroven,
)

from .models import FunkcePosadky, Posadka, StavLetu, ZpusobVzletu
from .obdobi import rozsah
from .vypis import letecky

OK, POZOR, CHYBA, INFO = "ok", "pozor", "chyba", "info"
ZPUSOBILOST, ROZLETANOST = "zpusobilost", "rozletanost"  # moduly hlídání
JAZYK = "Jazyková způsobilost"
BRZY = timedelta(days=30)  # varovat, když něco brzy vyprší
DNY_CESTUJICI = 90
MESICE_ZPET = 37  # nejdelší okno: prodloužení PPL (12 měsíců před koncem platnosti 24 měsíců)
DOZOR = (FunkcePosadky.ZAK, FunkcePosadky.PREZKOUSENY)  # let s instruktorem

# Způsob vzletu kluzáku v evidenci → kvalifikace SPL. Start gumou se neeviduje.
KVALIFIKACE_ZPUSOBU = {
    ZpusobVzletu.NAVIJAK: DruhKvalifikace.NAVIJAK,
    ZpusobVzletu.VLEK: DruhKvalifikace.VLEK,
    ZpusobVzletu.AUTOSTART: DruhKvalifikace.SAMOSTART,
}


def plus_mesice(den: date, mesicu: int) -> date:
    rok, mesic = divmod(den.month - 1 + mesicu, 12)
    rok, mesic = den.year + rok, mesic + 1
    return date(rok, mesic, min(den.day, calendar.monthrange(rok, mesic)[1]))


def datum(den: date | None) -> str:
    return f"{den.day}. {den.month}. {den.year}" if den else "–"


@dataclass
class Zaznam:
    """Jeden let z pohledu pilota."""

    den: date
    kategorie: str
    funkce: str
    minuty: int
    vzlety: int
    pristani: int
    zpusob: str

    @property
    def pic(self) -> bool:
        return self.funkce == FunkcePosadky.PIC

    @property
    def s_instruktorem(self) -> bool:
        return self.funkce in DOZOR


def zaznamy(osoba: Osoba, do: date) -> list[Zaznam]:
    zacatek, konec = rozsah(plus_mesice(do, -MESICE_ZPET), do)
    clenstvi = Posadka.objects.filter(
        osoba=osoba,
        funkce__in=[FunkcePosadky.PIC, *DOZOR],
        let__stav=StavLetu.UKONCEN,
        let__cas_vzletu__gte=zacatek,
        let__cas_vzletu__lt=konec,
    ).select_related("let__letadlo")
    vysledek = []
    for c in clenstvi:
        let = c.let
        vysledek.append(
            Zaznam(
                den=let.cas_vzletu.astimezone(UTC).date(),
                kategorie=let.letadlo.kategorie,
                funkce=c.funkce,
                minuty=let.doba_uctovana_min or 0,
                vzlety=let.pocet_pristani or 1,  # každé T&G je i vzlet
                pristani=let.pocet_pristani,
                zpusob=let.zpusob_vzletu,
            )
        )
    return vysledek


@dataclass
class Podminka:
    """Jedna číselná podmínka, např. „12 h jako PIC za 24 měsíců“."""

    nazev: str
    potreba: float
    hodnota: Callable[[Zaznam], float]
    jednotka: str = ""  # "min" = zobrazit jako dobu

    def popis(self, soucet: float) -> str:
        if self.jednotka == "min":
            return f"{self.nazev} {letecky(int(soucet))} / {letecky(int(self.potreba))}"
        return f"{self.nazev} {int(soucet)} / {int(self.potreba)}"


def vyhodnot(
    lety: list[Zaznam], podminky: list[Podminka], dnes: date, od: date, lhuta
) -> tuple[bool, date | None, list[str]]:
    """Splnění podmínek za období [od, dnes]; vrací (splněno, platí do, popisy)."""
    v_okne = sorted((z for z in lety if od <= z.den <= dnes), key=lambda z: z.den, reverse=True)
    splneno, konce, popisy = True, [], []
    for p in podminky:
        soucet, konec = 0.0, None
        for z in v_okne:
            soucet += p.hodnota(z)
            if konec is None and soucet >= p.potreba:
                konec = lhuta(z.den)
        popisy.append(("✓ " if soucet >= p.potreba else "✗ ") + p.popis(soucet))
        if konec is None:
            splneno = False
        else:
            konce.append(konec)
    return splneno, (min(konce) if splneno and konce else None), popisy


@dataclass
class Kontrola:
    oblast: str  # např. „Medical“, „LAPL(A)“, „SPL – naviják“
    nazev: str
    stav: str  # ok / pozor / chyba / info
    text: str
    plati_do: date | None = None
    podrobnosti: list[str] = field(default_factory=list)
    kategorie: str | None = None  # pro kterou kategorii letadel kontrola platí
    cestujici: bool = False  # jen pro let s cestujícími
    zpusob: str | None = None  # jen pro tento způsob vzletu kluzáku
    licence_typy: tuple = ()  # u medicalu: pro které licence platí
    modul: str = ZPUSOBILOST  # způsobilost (doklady), nebo rozlétanost (nálet)


def _stav_data(plati_do: date | None, dnes: date, brzy: timedelta = BRZY) -> str:
    if plati_do is None or plati_do < dnes:
        return CHYBA
    return POZOR if plati_do - dnes <= brzy else OK


def _medicaly(osoba: Osoba, licence: list[Licence], dnes: date) -> list[Kontrola]:
    """Medical pro každou skupinu licencí se stejnými požadavky na třídu.

    PPL(A) potřebuje třídu 1 nebo 2, LAPL(A), SPL a ULL stačí i LAPL. Jedno osvědčení
    může mít pro různé třídy různou platnost – rozhoduje nejdelší platnost vhodné třídy.
    """
    medicaly = list(Medical.objects.filter(osoba=osoba))
    skupiny: dict[tuple, list[str]] = {}
    for lic in licence:
        if lic.typ in MEDICAL_LICENCE:
            skupiny.setdefault(tuple(MEDICAL_LICENCE[lic.typ]), []).append(lic.typ)
    if not skupiny:
        skupiny = {tuple(TridaMedicalu.values): []}
    vysledek = []
    for tridy, typy in skupiny.items():
        nazev = "Medical"
        if len(skupiny) > 1:
            nazev += " pro " + ", ".join(TypLicence(t).label for t in typy)
        vhodne = [m for m in medicaly if m.trida in tridy]
        if not vhodne:
            text = "Není zadaný." if not medicaly else "Chybí vhodná třída."
            vysledek.append(Kontrola("Medical", nazev, CHYBA, text, licence_typy=tuple(typy)))
            continue
        nejlepsi = max(vhodne, key=lambda m: m.platnost_do)
        stav = _stav_data(nejlepsi.platnost_do, dnes)
        trida = nejlepsi.get_trida_display()
        text = (
            f"{trida} neplatí od {datum(nejlepsi.platnost_do + timedelta(1))}."
            if stav == CHYBA
            else f"{trida} platí do {datum(nejlepsi.platnost_do)}."
        )
        vysledek.append(
            Kontrola(
                "Medical",
                nazev,
                stav,
                text,
                plati_do=nejlepsi.platnost_do,
                licence_typy=tuple(typy),
            )
        )
    return vysledek


def _rolling(
    oblast: str,
    nazev: str,
    lety: list[Zaznam],
    podminky: list[Podminka],
    dnes: date,
    kategorie: str | None,
    mesicu: int = 24,
) -> Kontrola:
    splneno, plati_do, popisy = vyhodnot(
        lety, podminky, dnes, plus_mesice(dnes, -mesicu), lambda d: plus_mesice(d, mesicu)
    )
    if splneno:
        stav, text = _stav_data(plati_do, dnes), f"Splněno, platí do {datum(plati_do)}."
    else:
        stav, text = CHYBA, f"Nesplněno za posledních {mesicu} měsíců."
    return Kontrola(oblast, nazev, stav, text, plati_do, popisy, kategorie, modul=ROZLETANOST)


def _cestujici(oblast: str, lety: list[Zaznam], kategorie: str, dnes: date, co: str) -> Kontrola:
    if co == "starty":
        podminky = [Podminka("starty", 3, lambda z: 1)]
    else:
        podminky = [
            Podminka("vzlety", 3, lambda z: z.vzlety),
            Podminka("přistání", 3, lambda z: z.pristani),
        ]
    pic = [z for z in lety if z.pic and z.kategorie == kategorie]
    splneno, plati_do, popisy = vyhodnot(
        pic, podminky, dnes, dnes - timedelta(DNY_CESTUJICI), lambda d: d + timedelta(DNY_CESTUJICI)
    )
    nazev = f"Cestující – {dict(Kategorie.choices)[kategorie].lower()}"
    if splneno:
        stav, text = _stav_data(plati_do, dnes), f"Smí vozit cestující do {datum(plati_do)}."
    else:
        stav, text = POZOR, f"Za 90 dní nemá 3 {co} jako PIC – nesmí vozit cestující."
    return Kontrola(
        oblast, nazev, stav, text, plati_do, popisy, kategorie, cestujici=True, modul=ROZLETANOST
    )


def _platnost(oblast: str, nazev: str, plati_do: date | None, dnes: date, kat: str) -> Kontrola:
    if plati_do is None:
        return Kontrola(oblast, nazev, POZOR, "Chybí datum konce platnosti.", kategorie=kat)
    stav = _stav_data(plati_do, dnes)
    text = (
        f"Neplatí od {datum(plati_do + timedelta(1))}."
        if stav == CHYBA
        else f"Platí do {datum(plati_do)}."
    )
    return Kontrola(oblast, nazev, stav, text, plati_do, kategorie=kat)


def _radio(licence: Licence, dnes: date) -> list[Kontrola]:
    """Průkaz radiotelefonisty (ČTÚ): platí 10 let, prodlužuje se o 5 let."""
    kvalifikace = list(licence.kvalifikace.all())
    if not kvalifikace:
        return [Kontrola("Radiofonní průkaz", "Radiofonní průkaz", POZOR, "Chybí druh a platnost.")]
    vysledek = []
    for kv in kvalifikace:
        if kv.platnost_do is None:
            text = "Chybí datum platnosti."
            vysledek.append(Kontrola("Radiofonní průkaz", kv.get_druh_display(), POZOR, text))
            continue
        # Žádost o prodloužení se podává aspoň měsíc předem – varujeme 2 měsíce dopředu.
        stav = _stav_data(kv.platnost_do, dnes, brzy=timedelta(days=60))
        text = (
            f"Neplatí od {datum(kv.platnost_do + timedelta(1))}."
            if stav == CHYBA
            else f"Platí do {datum(kv.platnost_do)}."
        )
        k = Kontrola("Radiofonní průkaz", kv.get_druh_display(), stav, text, kv.platnost_do)
        if stav != OK:
            k.podrobnosti.append("Prodloužení o 5 let: žádost na ČTÚ aspoň měsíc před koncem.")
        vysledek.append(k)
    return vysledek


def _jazyk(licence: Licence, dnes: date) -> list[Kontrola]:
    """Jazyková způsobilost (FCL.055): úroveň 4 platí 4 roky, 5 šest let, 6 trvale."""
    kvalifikace = list(licence.kvalifikace.all())
    if not kvalifikace:
        return [Kontrola(JAZYK, JAZYK, POZOR, "Chybí jazyk a úroveň.")]
    vysledek = []
    for kv in kvalifikace:
        nazev = kv.get_druh_display()
        if kv.druh.endswith("_6"):
            vysledek.append(Kontrola(JAZYK, nazev, OK, "Platí trvale."))
        elif kv.platnost_do is None:
            vysledek.append(Kontrola(JAZYK, nazev, POZOR, "Chybí datum platnosti."))
        else:
            # Přezkoušení je potřeba domluvit včas – varujeme 3 měsíce předem.
            stav = _stav_data(kv.platnost_do, dnes, brzy=timedelta(days=90))
            text = (
                f"Neplatí od {datum(kv.platnost_do + timedelta(1))}."
                if stav == CHYBA
                else f"Platí do {datum(kv.platnost_do)}."
            )
            vysledek.append(Kontrola(JAZYK, nazev, stav, text, kv.platnost_do))
    return vysledek


def _ppl(licence: Licence, lety: list[Zaznam], dnes: date) -> list[Kontrola]:
    kontroly = []
    for kv in licence.kvalifikace.all():
        kat = Kategorie.MOTOR if kv.druh == DruhKvalifikace.SEP else Kategorie.TMG
        k = _platnost("PPL(A)", f"Kvalifikace {kv.get_druh_display()}", kv.platnost_do, dnes, kat)
        if kv.platnost_do and kv.platnost_do >= dnes:
            # Prodloužení zkušeností: 12 měsíců před koncem platnosti (FCL.740.A).
            zacatek = plus_mesice(kv.platnost_do, -12)
            if dnes < zacatek:
                k.podrobnosti.append(f"Prodloužení zkušeností jde splnit od {datum(zacatek)}.")
            else:
                lety_tridy = [z for z in lety if z.kategorie == kat]
                _, _, popisy = vyhodnot(
                    lety_tridy,
                    [
                        Podminka("doba celkem", 12 * 60, lambda z: z.minuty, "min"),
                        Podminka("jako PIC", 6 * 60, lambda z: z.minuty if z.pic else 0, "min"),
                        Podminka("vzlety", 12, lambda z: z.vzlety),
                        Podminka("přistání", 12, lambda z: z.pristani),
                        Podminka(
                            "s instruktorem",
                            60,
                            lambda z: z.minuty if z.s_instruktorem else 0,
                            "min",
                        ),
                    ],
                    dnes,
                    zacatek,
                    lambda d: d,
                )
                k.podrobnosti = ["Pro prodloužení zkušeností:", *popisy]
        kontroly.append(k)
    return kontroly


def _lapl(licence: Licence, lety: list[Zaznam], dnes: date) -> list[Kontrola]:
    letouny = [z for z in lety if z.kategorie in (Kategorie.MOTOR, Kategorie.TMG)]
    return [
        _rolling(
            "LAPL(A)",
            "Průběžná rozlétanost",
            letouny,
            [
                Podminka("jako PIC", 12 * 60, lambda z: z.minuty if z.pic else 0, "min"),
                Podminka("vzlety jako PIC", 12, lambda z: z.vzlety if z.pic else 0),
                Podminka("přistání jako PIC", 12, lambda z: z.pristani if z.pic else 0),
                Podminka(
                    "s instruktorem", 60, lambda z: z.minuty if z.s_instruktorem else 0, "min"
                ),
            ],
            dnes,
            None,
        )
    ]


def _spl(licence: Licence, lety: list[Zaznam], dnes: date, tmg_jinde: bool) -> list[Kontrola]:
    kluzaky = [z for z in lety if z.kategorie == Kategorie.KLUZAK]
    kontroly = [
        _rolling(
            "SPL",
            "Rozlétanost na kluzácích",
            kluzaky,
            [
                Podminka("doba", 5 * 60, lambda z: z.minuty, "min"),
                Podminka("starty", 15, lambda z: 1),
                Podminka("lety s instruktorem", 2, lambda z: 1 if z.s_instruktorem else 0),
            ],
            dnes,
            Kategorie.KLUZAK,
        )
    ]
    druhy = {kv.druh for kv in licence.kvalifikace.all()}
    for zpusob, druh in KVALIFIKACE_ZPUSOBU.items():
        if druh in druhy:
            k = _rolling(
                "SPL",
                f"Způsob vzletu: {DruhKvalifikace(druh).label.lower()}",
                [z for z in kluzaky if z.zpusob == zpusob],
                [Podminka("starty", 5, lambda z: 1)],
                dnes,
                Kategorie.KLUZAK,
            )
            k.zpusob = zpusob
            kontroly.append(k)
    if DruhKvalifikace.GUMA in druhy:
        kontroly.append(
            Kontrola("SPL", "Způsob vzletu: guma", INFO, "Starty gumou aplikace neeviduje.")
        )
    if DruhKvalifikace.TMG in druhy and not tmg_jinde:
        tmg = [z for z in lety if z.kategorie == Kategorie.TMG]
        kontroly.append(
            _rolling(
                "SPL",
                "Rozlétanost na TMG",
                kluzaky + tmg,
                [
                    Podminka("doba celkem", 12 * 60, lambda z: z.minuty, "min"),
                    Podminka(
                        "na TMG",
                        6 * 60,
                        lambda z: z.minuty if z.kategorie == Kategorie.TMG else 0,
                        "min",
                    ),
                    Podminka(
                        "vzlety na TMG",
                        12,
                        lambda z: z.vzlety if z.kategorie == Kategorie.TMG else 0,
                    ),
                    Podminka(
                        "přistání na TMG",
                        12,
                        lambda z: z.pristani if z.kategorie == Kategorie.TMG else 0,
                    ),
                    Podminka(
                        "s instruktorem na TMG",
                        60,
                        lambda z: (
                            z.minuty if z.s_instruktorem and z.kategorie == Kategorie.TMG else 0
                        ),
                        "min",
                    ),
                ],
                dnes,
                Kategorie.TMG,
            )
        )
    return kontroly


def _ull(licence: Licence, lety: list[Zaznam], dnes: date) -> list[Kontrola]:
    kontroly = []
    for kv in licence.kvalifikace.all():
        k = _platnost("ULL", "Platnost průkazu", kv.platnost_do, dnes, Kategorie.UL)
        if kv.platnost_do and kv.platnost_do < dnes - timedelta(90):
            k.podrobnosti.append("Propadlý déle než 90 dní: prodloužení po letu s inspektorem LAA.")
        minuty = sum(
            z.minuty for z in lety if z.kategorie == Kategorie.UL and z.den > plus_mesice(dnes, -24)
        )
        znak = "✓" if minuty >= 300 else "✗"
        k.podrobnosti.append(f'{znak} Pro prodloužení nálet za 2 roky {letecky(minuty)} / 5°0"')
        kontroly.append(k)
    return kontroly


def kontroly(osoba: Osoba, dnes: date | None = None) -> list[Kontrola]:
    """Všechny kontroly licencí, medicalu a rozlétanosti pilota k danému dni."""
    dnes = dnes or timezone.now().astimezone(UTC).date()
    lety = zaznamy(osoba, dnes)
    licence = list(Licence.objects.filter(osoba=osoba).prefetch_related("kvalifikace"))
    vysledek = _medicaly(osoba, licence, dnes)
    radio = [lic for lic in licence if lic.typ == TypLicence.RADIO]
    jazyk = [lic for lic in licence if lic.typ == TypLicence.JAZYK]
    licence = [lic for lic in licence if lic.typ not in (TypLicence.RADIO, TypLicence.JAZYK)]
    if radio:
        vysledek += _radio(radio[0], dnes)
    else:
        vysledek.append(Kontrola("Radiofonní průkaz", "Radiofonní průkaz", POZOR, "Není zadaný."))
    if jazyk:
        vysledek += _jazyk(jazyk[0], dnes)
    else:
        vysledek.append(Kontrola(JAZYK, JAZYK, POZOR, "Není zadaná."))
    if not licence:
        if Opravneni.objects.filter(osoba=osoba).exclude(uroven=Uroven.ZAK).exists() or not (
            Opravneni.objects.filter(osoba=osoba).exists()
        ):
            vysledek.append(Kontrola("Licence", "Licence", CHYBA, "Pilotní licence není zadaná."))
        else:  # žák licenci ještě mít nemůže
            k = Kontrola("Licence", "Licence", INFO, "Žák – zatím bez licence.")
            k.podrobnosti.append("Před prvním sólem potřebuje platný medical a radiofonní průkaz.")
            vysledek.append(k)
        return vysledek

    druhy = {(lic.typ, kv.druh) for lic in licence for kv in lic.kvalifikace.all()}
    tmg_fcl = any(d == DruhKvalifikace.TMG and t != TypLicence.SPL for t, d in druhy)
    for lic in licence:
        if lic.typ == TypLicence.PPL_A:
            vysledek += _ppl(lic, lety, dnes)
        elif lic.typ == TypLicence.LAPL_A:
            vysledek += _lapl(lic, lety, dnes)
        elif lic.typ == TypLicence.SPL:
            vysledek += _spl(lic, lety, dnes, tmg_jinde=tmg_fcl)
        elif lic.typ == TypLicence.ULL:
            vysledek += _ull(lic, lety, dnes)

    # Let s cestujícími (FCL.060, SFCL.160(e)) – podle kategorií, které licence pokrývají.
    if any(d == DruhKvalifikace.SEP for _, d in druhy):
        vysledek.append(_cestujici("Cestující", lety, Kategorie.MOTOR, dnes, "vzlety a přistání"))
    if any(d == DruhKvalifikace.TMG for _, d in druhy):
        vysledek.append(_cestujici("Cestující", lety, Kategorie.TMG, dnes, "vzlety a přistání"))
    if any(lic.typ == TypLicence.SPL for lic in licence):
        vysledek.append(_cestujici("Cestující", lety, Kategorie.KLUZAK, dnes, "starty"))
    return vysledek


# --- varování při zakládání letu ----------------------------------------------------------

# Která licence a kvalifikace opravňuje k letu v dané kategorii.
OPRAVNUJE = {
    Kategorie.MOTOR: [
        (TypLicence.PPL_A, DruhKvalifikace.SEP),
        (TypLicence.LAPL_A, DruhKvalifikace.SEP),
    ],
    Kategorie.TMG: [
        (TypLicence.PPL_A, DruhKvalifikace.TMG),
        (TypLicence.LAPL_A, DruhKvalifikace.TMG),
        (TypLicence.SPL, DruhKvalifikace.TMG),
    ],
    Kategorie.KLUZAK: [(TypLicence.SPL, None)],
    Kategorie.UL: [(TypLicence.ULL, None)],
}


def varovani_pilota(
    osoba: Osoba,
    kategorie: str,
    cestujici: bool,
    zpusob: str | None = None,
    moduly: frozenset = frozenset({ZPUSOBILOST, ROZLETANOST}),
) -> list[str]:
    """Co u PIC nesedí pro let v dané kategorii (jen varování, nic se neblokuje)."""
    if not moduly:
        return []
    jmeno = osoba.get_full_name()
    licence = list(Licence.objects.filter(osoba=osoba).prefetch_related("kvalifikace"))
    druhy = {(lic.typ, kv.druh) for lic in licence for kv in lic.kvalifikace.all()}
    typy = {lic.typ for lic in licence}
    povoleno = OPRAVNUJE[kategorie]
    if not any((t, d) in druhy if d else t in typy for t, d in povoleno):
        if ZPUSOBILOST not in moduly:
            return []  # bez licence nejde posoudit ani rozlétanost
        nazev = dict(Kategorie.choices)[kategorie].lower()
        return [f"{jmeno}: nemá zadanou licenci pro kategorii {nazev}."]

    # Licence, které let v této kategorii pokrývají – podle nich se posuzuje medical.
    kryji = {t for t, d in povoleno if ((t, d) in druhy if d else t in typy)}
    vysledek = []
    vse = [k for k in kontroly(osoba) if k.modul in moduly]
    # Jazyková způsobilost stačí v jednom jazyce (angličtina, nebo čeština v ČR).
    jazyky = [k for k in vse if k.oblast == JAZYK]
    neplatne = ("Není zadaná.", "Chybí jazyk a úroveň.")
    if jazyky and all(k.stav == CHYBA or k.text in neplatne for k in jazyky):
        vysledek.append(f"{jmeno}: nemá platnou jazykovou způsobilost.")
    for k in vse:
        if k.oblast == JAZYK:
            continue
        if k.oblast == "Radiofonní průkaz" and k.text == "Není zadaný.":
            vysledek.append(f"{jmeno}: nemá zadaný radiofonní průkaz.")
            continue
        if k.stav != CHYBA and not (k.cestujici and k.stav == POZOR):
            continue
        tyka_se = k.oblast in ("Medical", "Licence") or k.kategorie in (None, kategorie)
        if k.oblast == "Medical" and k.licence_typy and not kryji & set(k.licence_typy):
            tyka_se = False
        if k.oblast == "LAPL(A)" and kategorie not in (Kategorie.MOTOR, Kategorie.TMG):
            tyka_se = False
        if k.cestujici and (not cestujici or k.kategorie != kategorie):
            tyka_se = False
        if k.zpusob and k.zpusob != zpusob:
            tyka_se = False
        if tyka_se:
            vysledek.append(f"{jmeno}: {k.nazev} – {k.text}")
    if ZPUSOBILOST in moduly and zpusob in KVALIFIKACE_ZPUSOBU and kategorie == Kategorie.KLUZAK:
        druh = KVALIFIKACE_ZPUSOBU[zpusob]
        if (TypLicence.SPL, druh) not in druhy:
            vysledek.append(
                f"{jmeno}: nemá zadaný způsob vzletu {DruhKvalifikace(druh).label.lower()}."
            )
    return vysledek


def varovani_pred_solem(osoba: Osoba, dnes: date | None = None) -> list[str]:
    """Žák před sólem musí mít platný medical a radiofonní průkaz (licenci ještě ne)."""
    dnes = dnes or timezone.now().astimezone(UTC).date()
    jmeno = osoba.get_full_name()
    vysledek = []
    if not Medical.objects.filter(osoba=osoba, platnost_do__gte=dnes).exists():
        vysledek.append(f"{jmeno}: před sólem musí mít platný medical.")
    radio = Licence.objects.filter(
        osoba=osoba, typ=TypLicence.RADIO, kvalifikace__platnost_do__gte=dnes
    )
    if not radio.exists():
        vysledek.append(f"{jmeno}: před sólem musí mít platný radiofonní průkaz.")
    return vysledek
