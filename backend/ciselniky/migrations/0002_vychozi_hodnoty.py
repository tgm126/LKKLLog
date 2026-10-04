"""Výchozí hodnoty číselníků. Podklady: docs/licence-a-rozletanost.md.

Položky s kódem jsou systémové – počítají s nimi pravidla aplikace.
"""

from django.db import migrations

M, T, K, U = "motor", "tmg", "kluzak", "ul"

# (kód, název, skupina, kategorie, [(kód, název, má platnost, kategorie)])
PRUKAZY = [
    (
        "ppl_a",
        "PPL(A)",
        "pilotni",
        [M, T],
        [
            ("sep", "SEP (land)", True, [M]),
            ("tmg", "TMG", True, [T]),
            ("noc", "Noc (NIGHT)", False, []),
            ("akro", "Akrobacie", False, []),
            ("vlekani", "Vlekání kluzáků", False, [M, T]),
        ],
    ),
    (
        "lapl_a",
        "LAPL(A)",
        "pilotni",
        [M, T],
        [
            ("sep", "SEP (land)", False, [M]),
            ("tmg", "TMG", False, [T]),
            ("noc", "Noc (NIGHT)", False, []),
            ("akro", "Akrobacie", False, []),
            ("vlekani", "Vlekání kluzáků", False, [M, T]),
        ],
    ),
    (
        "spl",
        "SPL",
        "pilotni",
        [K, T],
        [
            ("navijak", "Naviják / auto", False, [K]),
            ("vlek", "Aerovlek", False, [K]),
            ("samostart", "Samostart", False, [K]),
            ("guma", "Guma (bungee)", False, [K]),
            ("tmg", "TMG", False, [T]),
            ("oblacnost", "Oblačnost", False, [K]),
            ("akro", "Akrobacie", False, [K]),
            ("vlekani", "Vlekání kluzáků (TMG)", False, [T]),
        ],
    ),
    ("ull", "Pilot ULL (LAA ČR)", "pilotni", [U], [("ull", "ULL", True, [U])]),
    (
        "instruktor",
        "Osvědčení instruktora",
        "instruktor",
        [],
        [
            ("fi_a", "FI(A)", True, [M, T]),
            ("cri_a", "CRI(A)", True, [M, T]),
            ("fi_s", "FI(S)", True, [K, T]),
            ("fi_s_omezeny", "FI(S) omezený", True, [K]),
            ("fi_ull", "Instruktor ULL", True, [U]),
        ],
    ),
    (
        "examinator",
        "Pověření examinátora",
        "examinator",
        [],
        [
            ("fe_a", "FE(A)", True, [M, T]),
            ("fe_s", "FE(S)", True, [K, T]),
            ("inspektor_laa", "Inspektor LAA", True, [U]),
        ],
    ),
    (
        "medical",
        "Medical",
        "medical",
        [],
        [("t1", "Třída 1", True, []), ("t2", "Třída 2", True, []), ("lapl", "LAPL", True, [])],
    ),
    (
        "radio",
        "Radiofonní průkaz (ČTÚ)",
        "radio",
        [],
        [("ofl", "Omezený (OFL)", True, []), ("vfl", "Všeobecný (VFL)", True, [])],
    ),
    (
        "jazyk",
        "Angličtina ICAO",
        "jazyk",
        [],
        [("en_4", "ICAO 4", True, []), ("en_5", "ICAO 5", True, []), ("en_6", "ICAO 6", False, [])],
    ),
]

PROVOZNI = [("navijakar", "Navijákář"), ("radio", "Služba RADIO"), ("vyhlidky", "Vyhlídkové lety")]

TERMINY = [
    "ARC",
    "Roční prohlídka",
    "50h prohlídka",
    "100h prohlídka",
    "Pojištění",
    "Generální oprava motoru (TBO)",
    "Vrtule",
    "Technický průkaz",
    "Záchranný systém",
]


def naplnit(apps, schema_editor):
    DruhPrukazu = apps.get_model("ciselniky", "DruhPrukazu")
    KvalifikacePrukazu = apps.get_model("ciselniky", "KvalifikacePrukazu")
    ProvozniOpravneni = apps.get_model("ciselniky", "ProvozniOpravneni")
    DruhTerminu = apps.get_model("ciselniky", "DruhTerminu")
    for i, (kod, nazev, skupina, kategorie, kvalifikace) in enumerate(PRUKAZY):
        druh = DruhPrukazu.objects.create(
            kod=kod, nazev=nazev, skupina=skupina, kategorie=kategorie, poradi=10 * (i + 1)
        )
        for j, (k_kod, k_nazev, platnost, k_kategorie) in enumerate(kvalifikace):
            KvalifikacePrukazu.objects.create(
                druh=druh,
                kod=k_kod,
                nazev=k_nazev,
                ma_platnost=platnost,
                kategorie=k_kategorie,
                poradi=10 * (j + 1),
            )
    for i, (kod, nazev) in enumerate(PROVOZNI):
        ProvozniOpravneni.objects.create(kod=kod, nazev=nazev, poradi=10 * (i + 1))
    for i, nazev in enumerate(TERMINY):
        DruhTerminu.objects.create(nazev=nazev, poradi=10 * (i + 1))


class Migration(migrations.Migration):
    dependencies = [("ciselniky", "0001_initial")]

    operations = [migrations.RunPython(naplnit, migrations.RunPython.noop)]
