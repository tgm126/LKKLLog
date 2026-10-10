"""Sazba PDF exportu letů (docs/modul-export.md, kap. 3) – A4 na šířku, písmo DejaVu Sans.

Jen sazba: data připraví `export.py` (dotazy), tady se nic nečte z databáze.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from fpdf import FPDF, FontFace

PISMA = Path(__file__).parent / "pisma"
DNY = ("pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle")
MESICE = (
    "leden", "únor", "březen", "duben", "květen", "červen",
    "červenec", "srpen", "září", "říjen", "listopad", "prosinec",
)  # fmt: skip
DRUH_PROVOZU = {"PLACHTARSKY": "Plachtařský provoz", "MOTOROVY": "Motorový provoz"}

# Sloupce tabulky letů: (záhlaví, poměrná šířka, zarovnání)
SLOUPCE = (
    ("č.", 6, "R"),
    ("Letadlo", 16, "L"),
    ("Typ", 15, "L"),
    ("PIC", 25, "L"),
    ("Další posádka", 33, "L"),
    ("Účel / úloha", 28, "L"),
    ("Vzlet (způsob)", 22, "L"),
    ("Odkud", 13, "L"),
    ("Kam", 13, "L"),
    ("Vzlet", 10, "C"),
    ("Přist.", 10, "C"),
    ("Doba", 10, "R"),
    ("Přist. č.", 9, "R"),
    ("POB", 8, "R"),
    ("Hradí", 26, "L"),
    ("Poznámka", 28, "L"),
)
SEDA = (225, 225, 225)
SVETLE_SEDA = (242, 242, 242)


@dataclass
class Let:
    den: date
    """Den letu (UTC datum vzletu, v_let.den)."""
    vzlet: datetime
    pristani: datetime
    rejstrik: str
    typ: str
    pic: str
    posadka: str
    ucel: str
    zpusob: str
    odkud: str
    kam: str
    doba_min: int
    pocet_pristani: int
    pob: int
    hradi: str
    poznamka: str
    soukrome: bool
    dodatecne: bool


@dataclass
class SouhrnLetadla:
    druh_provozu: str
    letadlo: str
    lety: int
    pristani: int
    minut: int
    navijaky: int


@dataclass
class SouhrnPlatce:
    platce: str
    letadlo: str
    lety: int
    minut: int
    klic: object = None
    """Kdo platí (id osoby, None = aeroklub) – dva lidé se stejným jménem se nesloučí."""


@dataclass
class Podklad:
    nazev_obdobi: str
    """„čtvrtek 9. 10. 2026“ nebo „říjen 2026“."""
    mesicni: bool
    lety: list[Let]
    letadla: list[SouhrnLetadla]
    platci: list[SouhrnPlatce]
    neukoncene: list[str] = field(default_factory=list)
    """Popisy letů ve vzduchu („OK-1234, vzlet 9. 10. 14:02“)."""
    vytvoreno: datetime = field(default_factory=datetime.now)
    vytvoril: str = ""
    verze: str = ""


def nazev_dne(den: date) -> str:
    return f"{DNY[den.weekday()]} {den.day}. {den.month}. {den.year}"


def nazev_mesice(den: date) -> str:
    return f"{MESICE[den.month - 1]} {den.year}"


def doba(minut: int) -> str:
    return f"{minut // 60}:{minut % 60:02d}"


def pocet_letu(n: int) -> str:
    return f"{n} {'let' if n == 1 else 'lety' if 2 <= n <= 4 else 'letů'}"


def _neukoncene(n: int) -> str:
    if n == 1:
        return "1 let není ukončený"
    if 2 <= n <= 4:
        return f"{n} lety nejsou ukončené"
    return f"{n} letů není ukončených"


class _Pdf(FPDF):
    def __init__(self, podklad: Podklad):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.podklad = podklad
        self.add_font("DejaVu", "", PISMA / "DejaVuSans.ttf")
        self.add_font("DejaVu", "B", PISMA / "DejaVuSans-Bold.ttf")
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(True, margin=14)
        self.alias_nb_pages()
        self.set_title(f"AK Kladno – záznam letů {podklad.nazev_obdobi}")
        self.set_author("AK Kladno Log")
        self.set_creation_date(podklad.vytvoreno)

    def header(self):
        self.set_font("DejaVu", "B", 12)
        self.cell(0, 6, f"AK Kladno – záznam letů: {self.podklad.nazev_obdobi}")
        self.set_font("DejaVu", "", 8)
        self.cell(0, 6, f"časy UTC · strana {self.page_no()}/{{nb}}", align="R")
        self.ln(8)

    def footer(self):
        self.set_y(-10)
        self.set_font("DejaVu", "", 7)
        p = self.podklad
        kdo = f" · {p.vytvoril}" if p.vytvoril else ""
        self.cell(
            0, 4, f"Vytvořeno {p.vytvoreno:%d. %m. %Y %H:%M} UTC{kdo} · AK Kladno Log {p.verze}"
        )


def _nadpis(pdf: _Pdf, text: str, velikost: int = 10) -> None:
    pdf.set_font("DejaVu", "B", velikost)
    pdf.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 7)


def _tabulka(pdf: _Pdf, zahlavi, sirky, zarovnani, radky, souctove=()) -> None:
    """Tabulka s opakovaným záhlavím; řádky s indexem v `souctove` tučně a podbarvené."""
    with pdf.table(
        col_widths=sirky,
        text_align=zarovnani,
        line_height=3.6,
        padding=0.8,
        headings_style=FontFace(emphasis="BOLD", fill_color=SEDA),
        borders_layout="SINGLE_TOP_LINE",
        repeat_headings=1,
        width=sum(sirky) if sum(sirky) < pdf.epw else pdf.epw,
        align="L",
    ) as t:
        t.row(zahlavi)
        for i, radek in enumerate(radky):
            styl = FontFace(emphasis="BOLD", fill_color=SVETLE_SEDA) if i in souctove else None
            t.row([str(h) for h in radek], style=styl)
    pdf.ln(3)


def _lety(pdf: _Pdf, lety: list[Let], cislo_od: int) -> None:
    radky = []
    for i, let_ in enumerate(lety, start=cislo_od):
        stitky = [s for s, ano in (("soukromé", let_.soukrome), ("dopsáno", let_.dodatecne)) if ano]
        poznamka = " · ".join([*stitky, let_.poznamka] if let_.poznamka else stitky)
        radky.append((
            i,
            let_.rejstrik,
            let_.typ,
            let_.pic,
            let_.posadka,
            let_.ucel,
            let_.zpusob,
            let_.odkud,
            let_.kam,
            f"{let_.vzlet:%H:%M}",
            f"{let_.pristani:%H:%M}",
            doba(let_.doba_min),
            let_.pocet_pristani,
            let_.pob,
            let_.hradi,
            poznamka,
        ))  # fmt: skip
    _tabulka(
        pdf,
        [s[0] for s in SLOUPCE],
        [s[1] for s in SLOUPCE],
        [s[2] for s in SLOUPCE],
        radky,
    )


def _souhrn_letadel(pdf: _Pdf, souhrn: list[SouhrnLetadla]) -> None:
    _nadpis(pdf, "Souhrn podle letadel")
    radky, souctove = [], []
    for druh, nazev in DRUH_PROVOZU.items():
        cast = [s for s in souhrn if s.druh_provozu == druh]
        if not cast:
            continue
        for s in cast:
            radky.append((nazev, s.letadlo, s.lety, s.pristani, doba(s.minut), s.navijaky))
        souctove.append(len(radky))
        radky.append((
            f"{nazev} celkem", "",
            sum(s.lety for s in cast), sum(s.pristani for s in cast),
            doba(sum(s.minut for s in cast)), sum(s.navijaky for s in cast),
        ))  # fmt: skip
    _tabulka(
        pdf,
        ["Provoz", "Letadlo", "Lety", "Přistání", "Doba", "Navijáky"],
        (40, 45, 15, 15, 18, 15),
        ("L", "L", "R", "R", "R", "R"),
        radky,
        souctove,
    )


def _souhrn_platcu(pdf: _Pdf, souhrn: list[SouhrnPlatce]) -> None:
    _nadpis(pdf, "Souhrn podle plátců")
    radky, souctove = [], []
    platci = list(dict.fromkeys((s.klic, s.platce) for s in souhrn))
    for klic, platce in platci:
        cast = [s for s in souhrn if (s.klic, s.platce) == (klic, platce)]
        for s in cast:
            radky.append((platce, s.letadlo, s.lety, doba(s.minut)))
        if len(cast) > 1:
            souctove.append(len(radky))
            radky.append((
                f"{platce} celkem", "", sum(s.lety for s in cast), doba(sum(s.minut for s in cast))
            ))  # fmt: skip
    _tabulka(
        pdf,
        ["Hradí", "Letadlo", "Lety", "Doba"],
        (55, 45, 15, 18),
        ("L", "L", "R", "R"),
        radky,
        souctove,
    )


def sazba(podklad: Podklad) -> bytes:
    pdf = _Pdf(podklad)
    pdf.add_page()
    pdf.set_font("DejaVu", "", 8)
    celkem = sum(let_.doba_min for let_ in podklad.lety)
    pdf.cell(
        0, 5, f"Ukončené lety: {len(podklad.lety)} · celková doba {doba(celkem)}",
        new_x="LMARGIN", new_y="NEXT",
    )  # fmt: skip
    if podklad.neukoncene:
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(170, 0, 0)
        pdf.multi_cell(
            0, 4,
            f"Pozor: {_neukoncene(len(podklad.neukoncene))} (v exportu chybí): "
            + "; ".join(podklad.neukoncene),
            new_x="LMARGIN", new_y="NEXT",
        )  # fmt: skip
        pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    pdf.set_font("DejaVu", "", 7)

    if podklad.mesicni:
        dny = list(dict.fromkeys(let_.den for let_ in podklad.lety))
        cislo = 1
        for den in dny:
            lety_dne = [let_ for let_ in podklad.lety if let_.den == den]
            minut = sum(let_.doba_min for let_ in lety_dne)
            _nadpis(pdf, f"{nazev_dne(den)} – {pocet_letu(len(lety_dne))}, {doba(minut)}", 9)
            _lety(pdf, lety_dne, cislo)
            cislo += len(lety_dne)
    else:
        _lety(pdf, podklad.lety, 1)

    _souhrn_letadel(pdf, podklad.letadla)
    _souhrn_platcu(pdf, podklad.platci)

    if pdf.will_page_break(20):
        pdf.add_page()
    pdf.ln(6)
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(
        0, 6,
        "Zkontroloval: ________________________________    dne: ________________"
        "    podpis: ________________________",
    )  # fmt: skip
    return bytes(pdf.output())
