"""Export záznamů o letech – PDF e-mailem adminům (docs/modul-export.md).

Smí osoba s právem `smi_exportovat` a admin, ne v relaci jen ke čtení. Jen ukončené lety
období (den letu = UTC datum vzletu); lety ve vzduchu PDF jen vyjmenuje. Záznam o odeslání
v lkkl.email (druh EXPORT_LETU, období), obsah ani PDF se neukládá.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from . import posta
from .db import spojeni
from .export_pdf import (
    Let,
    Podklad,
    SouhrnLetadla,
    SouhrnPlatce,
    nazev_dne,
    nazev_mesice,
    pocet_letu,
    sazba,
)
from .model import Model
from .nastaveni import nastaveni
from .prihlasovani import Prihlaseny, smi_exportovat
from .sprava import DenSLety

router = APIRouter(prefix="/api/export")

DruhExportu = Literal["DEN", "MESIC"]


class NabidkaExportu(Model):
    dny: list[DenSLety]
    adresy: list[str]
    """Komu export přijde (admini, kteří se smějí přihlásit)."""


class ExportIn(Model):
    druh: DruhExportu
    den: date
    """Exportovaný den; u měsíce kterýkoli den měsíce."""


class Odeslano(Model):
    obdobi: str
    """„čtvrtek 9. 10. 2026“ nebo „říjen 2026“."""
    lety: int
    adresy: list[str]


def obdobi(druh: DruhExportu, den: date) -> tuple[date, date, str]:
    """Dny [od, do) a název období."""
    if druh == "DEN":
        return den, den + timedelta(days=1), nazev_dne(den)
    od = den.replace(day=1)
    do = (od + timedelta(days=32)).replace(day=1)
    return od, do, nazev_mesice(od)


def _jmeno(prijmeni: str | None, jmeno: str | None) -> str:
    return f"{prijmeni} {jmeno}" if prijmeni else ""


_LETY_SQL = """
SELECT l.den, l.cas_vzletu, l.cas_pristani, l.rejstrik, l.typ, l.soukrome,
       l.pic_prijmeni, l.pic_jmeno, l.ucel, l.je_vlecny, l.vlecny_let_id, l.zpusob_vzletu,
       l.misto_vzletu, l.misto_pristani, l.doba_min, l.pocet_pristani, l.pob,
       l.plati_aeroklub, l.platce_prijmeni, l.platce_jmeno, l.poznamka, l.dodatecne,
       l.uloha_oznaceni, l.prezkouseni_kod,
       kluzak.rejstrik AS kluzak, vlecna.rejstrik AS vlecna,
       (SELECT string_agg(f.nazev || ': ' || o.prijmeni || ' ' || o.jmeno, ', '
                          ORDER BY f.poradi)
        FROM lkkl.posadka p
        JOIN lkkl.lov_funkce f ON f.id = p.funkce_id
        JOIN lkkl.lov_osoba o  ON o.id = p.osoba_id
        WHERE p.let_id = l.id AND f.kod <> 'PIC') AS posadka
FROM lkkl.v_let l
LEFT JOIN lkkl.let k            ON k.id = l.vleceny_let_id
LEFT JOIN lkkl.lov_letadlo kluzak ON kluzak.id = k.letadlo_id
LEFT JOIN lkkl.let v            ON v.id = l.vlecny_let_id
LEFT JOIN lkkl.lov_letadlo vlecna ON vlecna.id = v.letadlo_id
WHERE l.stav = 'UKONCEN' AND l.den >= %(od)s AND l.den < %(do)s
ORDER BY l.cas_vzletu, l.je_vlecny, l.id
"""


def _let(r: dict) -> Let:
    if r["je_vlecny"]:
        ucel = f"Vlek {r['kluzak']}"
    else:
        oznaceni = r["uloha_oznaceni"] or r["prezkouseni_kod"]
        ucel = f"{r['ucel']} {oznaceni}" if oznaceni else r["ucel"]
    return Let(
        den=r["den"],
        vzlet=r["cas_vzletu"].astimezone(UTC),
        pristani=r["cas_pristani"].astimezone(UTC),
        rejstrik=r["rejstrik"],
        typ=r["typ"],
        pic=_jmeno(r["pic_prijmeni"], r["pic_jmeno"]),
        posadka=r["posadka"] or "",
        ucel=ucel,
        zpusob=f"Aerovlek {r['vlecna']}" if r["vlecna"] else r["zpusob_vzletu"],
        odkud=r["misto_vzletu"] or "",
        kam=r["misto_pristani"] or "",
        doba_min=r["doba_min"],
        pocet_pristani=r["pocet_pristani"] or 0,
        pob=r["pob"] or 0,
        hradi="aeroklub"
        if r["plati_aeroklub"]
        else _jmeno(r["platce_prijmeni"], r["platce_jmeno"]),
        poznamka=r["poznamka"] or "",
        soukrome=r["soukrome"],
        dodatecne=r["dodatecne"],
    )


def podklad(
    conn: Connection, od: date, do: date
) -> tuple[list[Let], list[SouhrnLetadla], list[SouhrnPlatce], list[str]]:
    """Data exportu: lety, souhrn podle letadel, podle plátců a popisy letů ve vzduchu."""
    parametry = {"od": od, "do": do}
    lety = [_let(r) for r in conn.execute(_LETY_SQL, parametry).fetchall()]
    letadla = [
        SouhrnLetadla(
            druh_provozu=r["druh_provozu"],
            letadlo=r["rejstrik"]
            + (" ve vleku" if r["je_vlecny"] else "")
            + (" (soukromé)" if r["soukrome"] else ""),
            lety=r["lety"],
            pristani=r["pristani"] or 0,
            minut=r["minut"] or 0,
            navijaky=r["navijaky"],
        )
        for r in conn.execute(
            """SELECT s.druh_provozu, s.rejstrik, s.je_vlecny, a.soukrome,
                      sum(s.lety)::int AS lety, sum(s.pristani)::int AS pristani,
                      sum(s.minut)::int AS minut, sum(s.navijaky)::int AS navijaky
               FROM lkkl.v_souhrn_dne s JOIN lkkl.lov_letadlo a ON a.id = s.letadlo_id
               WHERE s.den >= %(od)s AND s.den < %(do)s
               GROUP BY s.druh_provozu, s.rejstrik, s.je_vlecny, a.soukrome
               ORDER BY s.druh_provozu DESC, s.je_vlecny, s.rejstrik""",
            parametry,
        ).fetchall()
    ]
    platci = [
        SouhrnPlatce(
            platce="aeroklub"
            if r["plati_aeroklub"]
            else _jmeno(r["platce_prijmeni"], r["platce_jmeno"]),
            letadlo=r["rejstrik"] + (" ve vleku" if r["je_vlecny"] else ""),
            lety=r["lety"],
            minut=r["minut"] or 0,
            klic=r["platce_id"],
        )
        for r in conn.execute(
            """SELECT plati_aeroklub, platce_id, platce_prijmeni, platce_jmeno, rejstrik,
                      je_vlecny, sum(lety)::int AS lety, sum(minut)::int AS minut
               FROM lkkl.v_souhrn_platce
               WHERE den >= %(od)s AND den < %(do)s
               GROUP BY plati_aeroklub, platce_id, platce_prijmeni, platce_jmeno, rejstrik,
                        je_vlecny
               ORDER BY plati_aeroklub, platce_prijmeni, platce_jmeno, platce_id,
                        je_vlecny, rejstrik""",
            parametry,
        ).fetchall()
    ]
    neukoncene = [
        f"{r['rejstrik']}, vzlet {_den_cas(r['cas_vzletu'])}"
        for r in conn.execute(
            """SELECT rejstrik, cas_vzletu FROM lkkl.v_let
               WHERE stav = 'VE_VZDUCHU' AND den >= %(od)s AND den < %(do)s
               ORDER BY cas_vzletu, id""",
            parametry,
        ).fetchall()
    ]
    return lety, letadla, platci, neukoncene


def _den_cas(cas: datetime) -> str:
    c = cas.astimezone(UTC)
    return f"{c.day}. {c.month}. {c:%H:%M}"


_ADMINI_SQL = """SELECT osoba_id, email FROM lkkl.v_ucet
                  WHERE admin AND smi_se_prihlasit ORDER BY prijmeni, jmeno, osoba_id"""


@router.get("", response_model=NabidkaExportu)
def nabidka(_: Prihlaseny = Depends(smi_exportovat), conn: Connection = Depends(spojeni)):
    """Dny s ukončenými lety a jejich počet (kalendář exportu) a komu export přijde."""
    dny = conn.execute(
        """SELECT den, count(*)::int AS lety FROM lkkl.v_let
           WHERE stav = 'UKONCEN' GROUP BY den ORDER BY den"""
    ).fetchall()
    adresy = [r["email"] for r in conn.execute(_ADMINI_SQL).fetchall()]
    return NabidkaExportu(dny=dny, adresy=adresy)


TEXT = """Dobrý den,

v příloze je záznam letů AK Kladno za období {obdobi} ({lety}, PDF).
Export vyžádal(a): {kdo}.{upozorneni}

AK Kladno Log
"""


@router.post("", response_model=Odeslano)
def exportovat(
    data: ExportIn, p: Prihlaseny = Depends(smi_exportovat), conn: Connection = Depends(spojeni)
):
    """Sestaví PDF a pošle ho každému adminovi, který se smí přihlásit (zatím napevno)."""
    od, do, nazev = obdobi(data.druh, data.den)
    if conn.execute(
        """SELECT 1 FROM lkkl.email
           WHERE druh = 'EXPORT_LETU' AND odeslal_id = %s AND chyba IS NULL
             AND kdy > now() - interval '1 minute'""",
        (p.osoba_id,),
    ).fetchone():
        raise HTTPException(429, "Export byl odeslán před chvílí – další jde poslat za minutu.")
    lety, letadla, platci, neukoncene = podklad(conn, od, do)
    if not lety:
        raise HTTPException(400, f"Za období {nazev} nejsou žádné ukončené lety.")
    admini = conn.execute(_ADMINI_SQL).fetchall()
    if not admini:
        raise HTTPException(400, "Není komu export poslat (žádný admin se nesmí přihlásit).")
    kdo = conn.execute(
        "SELECT jmeno || ' ' || prijmeni AS kdo FROM lkkl.lov_osoba WHERE id = %s",
        (p.osoba_id,),
    ).fetchone()["kdo"]
    pdf = sazba(
        Podklad(
            nazev_obdobi=nazev,
            mesicni=data.druh == "MESIC",
            lety=lety,
            letadla=letadla,
            platci=platci,
            neukoncene=neukoncene,
            vytvoreno=datetime.now(UTC),
            vytvoril=kdo,
            verze=nastaveni.verze,
        )
    )
    soubor = f"lety-{od:%Y-%m-%d}.pdf" if data.druh == "DEN" else f"lety-{od:%Y-%m}.pdf"
    upozorneni = (
        f"\n\nPozor: lety ve vzduchu v exportu chybí ({len(neukoncene)}): " + "; ".join(neukoncene)
        if neukoncene
        else ""
    )
    text = TEXT.format(obdobi=nazev, lety=pocet_letu(len(lety)), kdo=kdo, upozorneni=upozorneni)
    chyby = []
    for a in admini:
        try:
            posta.odeslat(a["email"], f"AK Kladno Log – lety {nazev}", text, (soubor, pdf))
            chyba = None
        except posta.ChybaPosty as e:
            chyba = str(e)
            chyby.append(f"{a['email']}: {chyba}")
        conn.execute(
            """INSERT INTO lkkl.email (druh, osoba_id, adresa, odeslal_id, chyba, obdobi)
               VALUES ('EXPORT_LETU', %s, %s, %s, %s, daterange(%s, %s))""",
            (a["osoba_id"], a["email"], p.osoba_id, chyba, od, do),
        )
    if chyby:
        raise HTTPException(502, "E-mail se nepodařilo odeslat: " + "; ".join(chyby))
    return Odeslano(obdobi=nazev, lety=len(lety), adresy=[a["email"] for a in admini])
