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
    ("č.", 5, "R"),
    ("Letadlo", 13, "L"),
    ("Typ", 15, "L"),
    ("PIC", 22, "L"),
    ("Další posádka", 32, "L"),
    ("Hradí", 22, "L"),
    ("Účel / úloha", 24, "L"),
    ("Vzlet (způsob)", 18, "L"),
    ("Odkud", 11, "L"),
    ("Kam", 11, "L"),
    ("Vzlet", 8, "C"),
    ("Přistání", 11, "C"),
    ("Doba", 8, "R"),
    ("Počet", 8, "R"),
    ("Poznámka", 32, "L"),
)
PISMO = 6
"""Velikost písma tabulek (pt)."""
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
class Podklad:
    nazev_obdobi: str
    """„čtvrtek 9. 10. 2026“ nebo „říjen 2026“."""
    mesicni: bool
    lety: list[Let]
    letadla: list[SouhrnLetadla]
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
    pdf.set_font("DejaVu", "", PISMO)


@dataclass
class Skupina:
    """Řádek skupiny přes celou šířku tabulky (letadlo)."""

    text: str


def _tabulka(pdf: _Pdf, zahlavi, sirky, zarovnani, radky, souctove=(), roztazena=False) -> None:
    """Mřížka s opakovaným záhlavím, text v buňkách nahoře; řádky s indexem v `souctove`
    tučně a podbarvené, `Skupina` přes celou šířku."""
    pdf.set_font("DejaVu", "", PISMO)
    pdf.set_draw_color(120, 120, 120)
    with pdf.table(
        col_widths=sirky,
        text_align=zarovnani,
        v_align="TOP",
        line_height=2.8,
        padding=0.7,
        headings_style=FontFace(emphasis="BOLD", fill_color=SEDA),
        borders_layout="ALL",
        repeat_headings=1,
        width=pdf.epw if roztazena else min(sum(sirky), pdf.epw),
        align="L",
    ) as t:
        t.row(zahlavi)
        tucne = FontFace(emphasis="BOLD", fill_color=SVETLE_SEDA)
        for i, radek in enumerate(radky):
            if isinstance(radek, Skupina):
                t.row().cell(radek.text, colspan=len(sirky), align="L", style=tucne)
            else:
                t.row([str(h) for h in radek], style=tucne if i in souctove else None)
    pdf.ln(3)


def _lety(pdf: _Pdf, lety: list[Let], cislo_od: int) -> None:
    """Lety seskupené podle letadla (vstup seřazený podle letadla a vzletu)."""
    radky: list = []
    letadla = list(dict.fromkeys(let_.rejstrik for let_ in lety))
    cislo = cislo_od
    for rejstrik in letadla:
        skupina = [let_ for let_ in lety if let_.rejstrik == rejstrik]
        prvni = skupina[0]
        soukrome = " (soukromé)" if prvni.soukrome else ""
        minut = sum(let_.doba_min for let_ in skupina)
        radky.append(
            Skupina(
                f"{rejstrik} · {prvni.typ}{soukrome} – {pocet_letu(len(skupina))}, {doba(minut)}"
            )
        )
        for let_ in skupina:
            stitky = [
                s for s, ano in (("soukromé", let_.soukrome), ("dopsáno", let_.dodatecne)) if ano
            ]
            poznamka = " · ".join([*stitky, let_.poznamka] if let_.poznamka else stitky)
            radky.append((
                cislo,
                let_.rejstrik,
                let_.typ,
                let_.pic,
                let_.posadka,
                let_.hradi,
                let_.ucel,
                let_.zpusob,
                let_.odkud,
                let_.kam,
                f"{let_.vzlet:%H:%M}",
                f"{let_.pristani:%H:%M}",
                doba(let_.doba_min),
                let_.pocet_pristani,
                poznamka,
            ))  # fmt: skip
            cislo += 1
    _tabulka(
        pdf,
        [s[0] for s in SLOUPCE],
        [s[1] for s in SLOUPCE],
        [s[2] for s in SLOUPCE],
        radky,
        roztazena=True,
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
