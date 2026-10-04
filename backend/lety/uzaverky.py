"""Denní a měsíční uzávěrky (kap. 4.7 návrhu).

Uzávěrka není zámek, ale uložený souhrn. Ukládá i verzi každého letu v období, takže
se dá kdykoli zjistit, co se změnilo potom (přehled „Změny po uzávěrce“). Přepočet
vytvoří novou verzi souhrnu, staré zůstávají v historii.
"""

import io
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from openpyxl import Workbook

from osoby.models import Osoba
from provoz.models import Nastaveni

from . import audit, vypis
from .models import AuditLog, FunkcePosadky, Let, StavLetu, Ucel, Uzaverka, ZpusobVzletu
from .obdobi import MESIC, Uzavreno, dalsi_mesic, den_letu, rozsah, zacatek_mesice
from .sluzby import ChybaLetu

Typ = Uzaverka.Typ
FUNKCE_NALETU = (FunkcePosadky.PIC, FunkcePosadky.ZAK, FunkcePosadky.PREZKOUSENY)
SOUCTY = ("lety", "minuty", "pristani", "tg", "navijak", "vlek")


# --- kdo smí uzavírat -------------------------------------------------------------


def smi_uzavrit_den(osoba: Osoba, den: date, uzavreno: Uzavreno) -> bool:
    if osoba.is_staff or osoba.role_ucetni:
        return True
    return osoba.role_casomeric and uzavreno.stav(den) != MESIC


def smi_uzavrit_mesic(osoba: Osoba) -> bool:
    return osoba.is_staff or osoba.role_ucetni


# --- data období ----------------------------------------------------------------------


def lety_obdobi(od: date, do: date) -> list[Let]:
    """Všechny lety se vzletem v období, včetně zrušených a soukromých."""
    zacatek, konec = rozsah(od, do)
    return list(
        Let.objects.select_related("letadlo", "platce")
        .prefetch_related("posadka__osoba")
        .filter(cas_vzletu__gte=zacatek, cas_vzletu__lt=konec)
        .order_by("cas_vzletu", "id")
    )


def souhrn(seznam: list[Let]) -> dict:
    """Souhrn uzávěrky. Počítají se ukončené lety klubových letadel; soukromá zvlášť."""
    klubove = [let for let in seznam if not let.soukrome]
    vysledek = vypis.souhrn(klubove)
    ukoncene = [let for let in klubove if let.stav == StavLetu.UKONCEN]

    # Starty kluzáků a letadel; let vlečné je součástí startu vlekem, nepočítá se zvlášť.
    starty = {z: 0 for z in ZpusobVzletu.values}
    for let in ukoncene:
        if let.ucel != Ucel.VLEK:
            starty[let.zpusob_vzletu] += 1

    funkce = dict(FunkcePosadky.choices)
    osoby: dict[tuple, dict] = defaultdict(lambda: {"lety": 0, "minuty": 0})
    for let in ukoncene:
        for clen in let.posadka.all():
            if clen.funkce in FUNKCE_NALETU:
                radek = osoby[(clen.osoba.prijmeni, clen.osoba.jmeno, clen.osoba_id, clen.funkce)]
                radek["lety"] += 1
                radek["minuty"] += let.doba_uctovana_min or 0

    soukrome = [let for let in seznam if let.soukrome and let.stav == StavLetu.UKONCEN]
    vysledek.update(
        {
            "starty": starty,
            "podle_osob": [
                {
                    "osoba_id": k[2],
                    "osoba": f"{k[1]} {k[0]}".strip(),
                    "funkce": funkce[k[3]],
                    **v,
                }
                for k, v in sorted(osoby.items())
            ],
            "soukrome": {
                "lety": len(soukrome),
                "minuty": sum(let.doba_uctovana_min or 0 for let in soukrome),
            },
            # Verze každého letu: podle nich se pozná, co se po uzávěrce změnilo.
            "lety": {str(let.pk): let.verze for let in seznam},
        }
    )
    return vysledek


def _zmenene(ulozeny: dict, seznam: list[Let]) -> list[int]:
    pred = ulozeny.get("lety", {})
    ted = {str(let.pk): let.verze for let in seznam}
    return sorted(int(k) for k in pred.keys() | ted.keys() if pred.get(k) != ted.get(k))


def _rozsah_uzaverky(typ: str, obdobi: date) -> tuple[date, date]:
    if typ == Typ.DEN:
        return obdobi, obdobi
    return obdobi, dalsi_mesic(obdobi) - timedelta(days=1)


def platne(od: date, do: date) -> dict[tuple[str, date], Uzaverka]:
    """Poslední platná verze každé uzávěrky v rozmezí období."""
    vysledek = {}
    for u in (
        Uzaverka.objects.select_related("uzavrel")
        .filter(znovu_otevreno__isnull=True, obdobi__gte=od, obdobi__lte=do)
        .order_by("verze")
    ):
        vysledek[(u.typ, u.obdobi)] = u
    return vysledek


def info(u: Uzaverka | None) -> dict | None:
    if u is None:
        return None
    return {
        "id": u.pk,
        "typ": u.typ,
        "obdobi": u.obdobi,
        "verze": u.verze,
        "kdy": u.kdy,
        "uzavrel": u.uzavrel.get_full_name() if u.uzavrel else "automaticky",
        "platna": u.znovu_otevreno is None,
    }


# --- příprava a uložení -----------------------------------------------------------------


@dataclass
class Priprava:
    typ: str
    obdobi: date
    od: date
    do: date
    seznam: list[Let]
    zakaz: str | None = None  # proč uživatel nesmí uzavřít
    neukonceno: list[str] = field(default_factory=list)
    neuzavrene_dny: list[date] = field(default_factory=list)
    posledni: Uzaverka | None = None

    @property
    def lze(self) -> bool:
        return not (self.zakaz or self.neukonceno or self.neuzavrene_dny)


def _neukoncene(od: date, do: date, dnes: date) -> list[str]:
    zacatek, konec = rozsah(od, do)
    podminka = Q(stav=StavLetu.VE_VZDUCHU, cas_vzletu__gte=zacatek, cas_vzletu__lt=konec) | Q(
        stav=StavLetu.PRIPRAVEN, zalozeno__gte=zacatek, zalozeno__lt=konec
    )
    if od <= dnes <= do:  # dnes se počítá všechno, co ještě neskončilo (jako v přehledu)
        podminka |= Q(stav__in=[StavLetu.PRIPRAVEN, StavLetu.VE_VZDUCHU])
    stav = dict(StavLetu.choices)
    return [
        f"{let.letadlo.imatrikulace} ({stav[let.stav].lower()})"
        for let in Let.objects.select_related("letadlo").filter(podminka).order_by("id")
    ]


def priprav(typ: str, obdobi: date, kdo: Osoba) -> Priprava:
    dnes = timezone.now().astimezone(UTC).date()
    uzavreno = Uzavreno.nacti()
    if typ == Typ.DEN:
        if obdobi > dnes:
            raise ChybaLetu("Den, který ještě nezačal, nejde uzavřít.")
        zakaz = None
        if not smi_uzavrit_den(kdo, obdobi, uzavreno):
            zakaz = (
                "Měsíc je uzavřený – souhrn dne přepočítá účetní."
                if kdo.role_casomeric
                else "Den uzavírá časoměřič, účetní nebo admin."
            )
    elif typ == Typ.MESIC:
        obdobi = zacatek_mesice(obdobi)
        zakaz = None if smi_uzavrit_mesic(kdo) else "Měsíc uzavírá účetní nebo admin."
    else:
        raise ChybaLetu("Neznámý typ uzávěrky.")

    od, do = _rozsah_uzaverky(typ, obdobi)
    if typ == Typ.MESIC and do >= dnes and not zakaz:
        zakaz = "Měsíc ještě neskončil."
    p = Priprava(typ, obdobi, od, do, lety_obdobi(od, do), zakaz=zakaz)
    p.neukonceno = _neukoncene(od, do, dnes)
    if typ == Typ.MESIC:
        dny = {den_letu(let) for let in p.seznam if let.stav != StavLetu.ZRUSEN}
        p.neuzavrene_dny = sorted(d for d in dny if d not in uzavreno.dny)
    p.posledni = Uzaverka.objects.filter(typ=typ, obdobi=obdobi).order_by("-verze").first()
    return p


@transaction.atomic
def uzavrit(typ: str, obdobi: date, kdo: Osoba) -> Uzaverka:
    """Uloží souhrn období. Je-li období už uzavřené, vznikne nová verze (přepočet)."""
    p = priprav(typ, obdobi, kdo)
    if p.zakaz:
        raise ChybaLetu(p.zakaz, status=403)
    if p.neukonceno:
        raise ChybaLetu(
            "Nejdřív ukončete nebo zrušte lety: " + ", ".join(p.neukonceno) + ".",
            status=409,
            kod="neukonceno",
        )
    if p.neuzavrene_dny:
        raise ChybaLetu(
            "Nejdřív uzavřete dny: " + ", ".join(f"{d.day}.{d.month}." for d in p.neuzavrene_dny),
            status=409,
            kod="neuzavrene_dny",
        )
    return _ulozit(p, kdo)


def _ulozit(p: Priprava, kdo: Osoba | None) -> Uzaverka:
    try:
        with transaction.atomic():
            u = Uzaverka.objects.create(
                typ=p.typ,
                obdobi=p.obdobi,
                verze=p.posledni.verze + 1 if p.posledni else 1,
                uzavrel=kdo,
                souhrn=souhrn(p.seznam),
            )
    except IntegrityError as e:
        raise ChybaLetu(
            "Uzávěrku tohoto období právě uložil někdo jiný.", status=409, kod="zmeneno"
        ) from e
    zmeny = {"typ": u.typ, "obdobi": u.obdobi.isoformat(), "verze": u.verze}
    if kdo is None:
        zmeny["automaticky"] = True
    audit.zapsat(kdo, "uzaverka", "uzaverka", u.pk, zmeny=zmeny)
    return u


AUTOMATICKY_ZPET = timedelta(days=31)


def uzavrit_automaticky(ted: datetime | None = None) -> list[Uzaverka]:
    """Uzavře minulé dny, kdy se létalo, pokud v nich nic neletí ani není připravené.

    Spouští ho cron serveru každý den v 5:00 (český čas), takže se uzavírá předchozí den
    a piloti mají celý večer na dopsání letů. Dnešek se nikdy neuzavírá. Den, který už
    někdy uzavřený byl (i když ho admin znovu otevřel), nechává lidem. Neukončený let
    den neuzavře – zkusí se to znovu další ráno.
    """
    nastaveni = Nastaveni.aktualni()
    if not nastaveni.automaticka_uzaverka:
        return []
    ted = ted or timezone.now()
    dnes = ted.astimezone(UTC).date()
    zacatek, konec = rozsah(dnes - AUTOMATICKY_ZPET, dnes - timedelta(days=1))
    dny = {
        den_letu(let)
        for let in Let.objects.filter(cas_vzletu__gte=zacatek, cas_vzletu__lt=konec)
        .exclude(stav=StavLetu.ZRUSEN)
        .only("cas_vzletu")
    }
    uz_byly = set(
        Uzaverka.objects.filter(typ=Typ.DEN, obdobi__in=dny).values_list("obdobi", flat=True)
    )
    uzavreno = Uzavreno.nacti()
    vysledek = []
    for den in sorted(dny - uz_byly):
        if uzavreno.stav(den) == MESIC or _neukoncene(den, den, dnes):
            continue
        p = Priprava(Typ.DEN, den, den, den, lety_obdobi(den, den))
        with transaction.atomic():
            vysledek.append(_ulozit(p, None))
    return vysledek


@transaction.atomic
def znovu_otevrit(typ: str, obdobi: date, kdo: Osoba) -> int:
    """Admin zruší platnost uzávěrky; verze zůstanou v historii. Vrací počet verzí."""
    pocet = Uzaverka.objects.filter(typ=typ, obdobi=obdobi, znovu_otevreno__isnull=True).update(
        znovu_otevreno=timezone.now()
    )
    if pocet:
        posledni = Uzaverka.objects.filter(typ=typ, obdobi=obdobi).order_by("-verze").first()
        audit.zapsat(
            kdo,
            "otevreni",
            "uzaverka",
            posledni.pk,
            zmeny={"typ": typ, "obdobi": obdobi.isoformat()},
        )
    return pocet


# --- přehled měsíce a změny po uzávěrce ------------------------------------------------


def prehled_mesice(mesic: date, kdo: Osoba) -> dict:
    mesic = zacatek_mesice(mesic)
    od, do = _rozsah_uzaverky(Typ.MESIC, mesic)
    dnes = timezone.now().astimezone(UTC).date()
    seznam = lety_obdobi(od, do)
    po_dnech: dict[date, list[Let]] = defaultdict(list)
    for let in seznam:
        po_dnech[den_letu(let)].append(let)
    uzaverky = platne(od, do)
    uzavreno = Uzavreno.nacti()

    dny = []
    for den in sorted(set(po_dnech) | {o for t, o in uzaverky if t == Typ.DEN}, reverse=True):
        lety = po_dnech.get(den, [])
        u = uzaverky.get((Typ.DEN, den))
        dny.append(
            {
                "den": den,
                "lety": sum(1 for let in lety if let.stav != StavLetu.ZRUSEN),
                "minuty": sum(
                    let.doba_uctovana_min or 0 for let in lety if let.stav == StavLetu.UKONCEN
                ),
                "neukonceno": sum(
                    1 for let in lety if let.stav in (StavLetu.VE_VZDUCHU, StavLetu.PRIPRAVEN)
                ),
                "uzaverka": info(u),
                "zmeny": len(_zmenene(u.souhrn, lety)) if u else 0,
                "smi_uzavrit": den <= dnes and smi_uzavrit_den(kdo, den, uzavreno),
            }
        )
    u_mesic = uzaverky.get((Typ.MESIC, mesic))
    return {
        "mesic": mesic,
        "dny": dny,
        "uzaverka": info(u_mesic),
        "zmeny": len(_zmenene(u_mesic.souhrn, seznam)) if u_mesic else 0,
        "skoncil": do < dnes,
        "smi_uzavrit": smi_uzavrit_mesic(kdo),
    }


def stav_dne(den: date, kdo: Osoba) -> dict:
    """Stav uzávěrky pro přehled dne."""
    dnes = timezone.now().astimezone(UTC).date()
    uzavreno = Uzavreno.nacti()
    u = platne(den, den).get((Typ.DEN, den))
    return {
        "uzaverka": info(u),
        "mesic_uzavren": uzavreno.stav(den) == MESIC,
        "zmeny": len(_zmenene(u.souhrn, lety_obdobi(den, den))) if u else 0,
        "smi_uzavrit": den <= dnes and smi_uzavrit_den(kdo, den, uzavreno),
    }


NAZVY_ZMEN = {
    "zalozeni": "Založení",
    "vzlet": "Vzlet",
    "tg": "Touch-and-go",
    "pristani": "Přistání",
    "zruseni": "Zrušení",
    "oprava": "Oprava",
    "zpet": "Vráceno tlačítkem Zpět",
    "upozorneni": "Odesláno upozornění",
}


def detail(typ: str, obdobi: date) -> dict:
    """Verze uzávěrky a co se změnilo od poslední platné verze."""
    if typ == Typ.MESIC:
        obdobi = zacatek_mesice(obdobi)
    verze = list(
        Uzaverka.objects.select_related("uzavrel").filter(typ=typ, obdobi=obdobi).order_by("-verze")
    )
    if not verze:
        raise ChybaLetu("Období není uzavřené.", status=404)
    od, do = _rozsah_uzaverky(typ, obdobi)
    seznam = lety_obdobi(od, do)
    posledni = next((u for u in verze if u.znovu_otevreno is None), None)
    vysledek = {
        "typ": typ,
        "obdobi": obdobi,
        "verze": [info(u) for u in verze],
        "souhrn": posledni.souhrn if posledni else None,
        "rozdil": None,
        "lety": [],
    }
    if posledni is None:
        return vysledek
    ids = _zmenene(posledni.souhrn, seznam)
    if not ids:
        return vysledek

    ted = souhrn(seznam)
    pred = posledni.souhrn
    vysledek["rozdil"] = {
        "celkem": {k: ted["celkem"][k] - pred["celkem"].get(k, 0) for k in SOUCTY},
        "starty": {k: v - pred.get("starty", {}).get(k, 0) for k, v in ted["starty"].items()},
    }
    zaznamy = defaultdict(list)
    for z in (
        AuditLog.objects.select_related("kdo")
        .filter(objekt="let", objekt_id__in=ids, kdy__gt=posledni.kdy)
        .order_by("kdy", "id")
    ):
        zaznamy[z.objekt_id].append(
            {
                "kdy": z.kdy,
                "kdo": z.kdo.get_full_name() if z.kdo else "systém",
                "akce": NAZVY_ZMEN.get(z.akce, z.akce),
                "zmeny": z.zmeny,
                "duvod": z.duvod,
                "poznamka": z.poznamka,
            }
        )
    for let in Let.objects.select_related("letadlo").filter(pk__in=ids).order_by("cas_vzletu"):
        vysledek["lety"].append(
            {
                "id": let.pk,
                "imatrikulace": let.letadlo.imatrikulace,
                "cas_vzletu": let.cas_vzletu,
                "cas_pristani": let.cas_pristani,
                "stav": let.stav,
                "doba_uctovana_min": let.doba_uctovana_min,
                "zaznamy": zaznamy.get(let.pk, []),
            }
        )
    return vysledek


# --- export souhrnu ---------------------------------------------------------------------


def excel(u: Uzaverka) -> bytes:
    s = u.souhrn
    wb = Workbook()
    wb.remove(wb.active)
    obdobi = f"{u.obdobi:%d.%m.%Y}" if u.typ == Typ.DEN else f"{u.obdobi:%m/%Y}"
    vypis._list(
        wb,
        "Uzávěrka",
        ["Údaj", "Hodnota"],
        [
            ["Uzávěrka", f"{u.get_typ_display()} {obdobi}"],
            ["Verze", u.verze],
            ["Uzavřeno (UTC)", u.kdy.astimezone(UTC).strftime("%d.%m.%Y %H:%M")],
            ["Uzavřel", u.uzavrel.get_full_name() if u.uzavrel else "automaticky po soumraku"],
            ["Platná", "ne – znovu otevřeno" if u.znovu_otevreno else "ano"],
            ["Počítají se", "ukončené lety klubových letadel"],
            [
                "Soukromá letadla (jen pro informaci)",
                f"{s['soukrome']['lety']} letů, {vypis.letecky(s['soukrome']['minuty'])}",
            ],
            ["Zrušené lety", s["zruseno"]],
        ],
    )
    hlavicka = ["Lety", "Minuty", "Doba", "Přistání", "Starty navijákem", "Vleky"]

    def hodnoty(r):
        doba = vypis.letecky(r["minuty"])
        return [r["lety"], r["minuty"], doba, r.get("pristani", ""), r["navijak"], r["vlek"]]

    vypis._list(
        wb,
        "Podle letadel",
        ["Letadlo", "Typ", "Účel", *hlavicka],
        [[r["imatrikulace"], r["typ"], r["ucel"], *hodnoty(r)] for r in s["podle_letadel"]]
        + [["Celkem", "", "", *hodnoty(s["celkem"])]],
    )
    vypis._list(
        wb,
        "Podle plátců",
        ["Platí", *hlavicka],
        [[r["platce"], *hodnoty(r)] for r in s["podle_platcu"]]
        + [["Celkem", *hodnoty(s["celkem"])]],
    )
    vypis._list(
        wb,
        "Podle osob",
        ["Osoba", "Funkce", "Lety", "Minuty", "Doba"],
        [
            [r["osoba"], r["funkce"], r["lety"], r["minuty"], vypis.letecky(r["minuty"])]
            for r in s["podle_osob"]
        ],
    )
    zpusob = dict(ZpusobVzletu.choices)
    vypis._list(
        wb,
        "Starty",
        ["Způsob vzletu", "Počet"],
        [[zpusob.get(k, k), v] for k, v in s["starty"].items()],
    )
    vystup = io.BytesIO()
    wb.save(vystup)
    return vystup.getvalue()
