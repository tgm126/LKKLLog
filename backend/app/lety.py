"""Lety: přehled dne a sluneční časy (návrh: docs/modul-lety.md)."""

from datetime import UTC, date, datetime, timedelta

from astral import Observer
from astral.sun import sun
from fastapi import APIRouter, Depends
from psycopg import Connection
from pydantic import BaseModel

from .db import spojeni
from .prihlasovani import Prihlaseny, prihlaseny

router = APIRouter(prefix="/api")


# --- schémata -------------------------------------------------------------------------------


class Slunce(BaseModel):
    """Začátek a konec občanského soumraku a východ a západ slunce (UTC)."""

    tb: datetime | None
    sr: datetime | None
    ss: datetime | None
    te: datetime | None


class Den(BaseModel):
    den: date
    ted: datetime
    """Čas serveru – obrazovka podle něj počítá stopky (hodiny telefonu se mohou lišit)."""
    domovske: str | None
    """Kód domovského letiště (místo se na páscích uvádí, jen když je jiné)."""
    slunce: Slunce


class Clen(BaseModel):
    jmeno: str
    prijmeni: str
    funkce: str
    funkce_kod: str


class Pasek(BaseModel):
    """Let pro pásek v přehledu dne."""

    id: int
    stav: str
    """NAPLANOVAN | VE_VZDUCHU | UKONCEN | ZRUSEN"""
    rejstrik: str
    typ: str
    kategorie_kod: str
    ucel: str | None
    ucel_kod: str | None
    zpusob_vzletu: str
    zpusob_vzletu_kod: str
    je_vlecny: bool
    vlecny_let_id: int | None
    """U vlečeného letu (kluzák): let vlečné."""
    vleceny_let_id: int | None
    """U vlečného letu: let kluzáku."""
    vlek_rejstrik: str | None
    """Druhé letadlo vleku (u kluzáku vlečná, u vlečné kluzák)."""
    misto_vzletu: str | None
    """Jen když není domovské."""
    misto_pristani: str | None
    """Jen když není domovské."""
    cas_vzletu: datetime | None
    cas_pristani: datetime | None
    doba_uctovana_min: int | None
    pocet_pristani: int | None
    pob: int | None
    """Jen zadaný počet (u výcviku, sóla a přezkoušení se odvozuje z posádky a neukazuje)."""
    pocet_tg: int
    posadka: list[Clen]
    duvod_zruseni: str | None
    zruseno: datetime | None
    dodatecne: bool
    zalozeno: datetime
    varovani: str | None
    """Proč je pásek červený (po konci soumraku, přes maximální dobu letu)."""


class LetyDne(BaseModel):
    ted: datetime
    lety: list[Pasek]


# --- pomocné --------------------------------------------------------------------------------


def _den_a_domovske(conn: Connection, den: date | None) -> tuple[date, datetime, dict | None]:
    r = conn.execute(
        """SELECT (now() AT TIME ZONE 'UTC')::date AS dnes, now() AS ted,
                  (SELECT json_build_object('kod', kod, 'sirka', zem_sirka, 'delka', zem_delka)
                   FROM lkkl.lov_letiste WHERE domovske) AS domovske"""
    ).fetchone()
    return den or r["dnes"], r["ted"], r["domovske"]


def slunce(domovske: dict | None, den: date) -> Slunce:
    """Sluneční časy pro souřadnice domovského letiště (knihovna astral, soumrak 6°)."""
    if not domovske or domovske["sirka"] is None or domovske["delka"] is None:
        return Slunce(tb=None, sr=None, ss=None, te=None)
    s = sun(Observer(float(domovske["sirka"]), float(domovske["delka"])), den, tzinfo=UTC)
    return Slunce(tb=s["dawn"], sr=s["sunrise"], ss=s["sunset"], te=s["dusk"])


def doba(minut: int) -> str:
    """Doba letu zápisem 1°02" (hodiny a minuty), pod hodinu 45"."""
    return f'{minut // 60}°{minut % 60:02d}"' if minut >= 60 else f'{minut}"'


def varovani(let: dict, ted: datetime, te: datetime | None) -> str | None:
    if let["stav"] != "VE_VZDUCHU":
        return None
    duvody = []
    if te and ted > te:
        duvody.append(f"Po konci občanského soumraku (TE {te:%H:%M})")
    if let["max_doba_min"] and ted - let["cas_vzletu"] > timedelta(minutes=let["max_doba_min"]):
        duvody.append(f"Přes maximální dobu letu ({doba(let['max_doba_min'])})")
    return " · ".join(duvody) or None


# --- adresy ---------------------------------------------------------------------------------


@router.get("/den", response_model=Den)
def den_info(
    den: date | None = None,
    _: Prihlaseny = Depends(prihlaseny),
    conn: Connection = Depends(spojeni),
):
    """Den do hlavičky: datum, čas serveru, domovské letiště a sluneční časy."""
    den, ted, domovske = _den_a_domovske(conn, den)
    return Den(
        den=den,
        ted=ted,
        domovske=domovske["kod"] if domovske else None,
        slunce=slunce(domovske, den),
    )


@router.get("/lety", response_model=LetyDne)
def lety(
    den: date | None = None,
    _: Prihlaseny = Depends(prihlaseny),
    conn: Connection = Depends(spojeni),
):
    """Lety dne pro pásky; dnes i všechno, co je ve vzduchu (i kdyby vzlétlo včera)."""
    den, ted, domovske = _den_a_domovske(conn, den)
    domovsky_kod = domovske["kod"] if domovske else None
    radky = conn.execute(
        """SELECT v.id, v.stav, v.rejstrik, v.typ, v.kategorie_kod, v.ucel, v.ucel_kod,
                  v.zpusob_vzletu, v.zpusob_vzletu_kod, v.je_vlecny, v.vlecny_let_id,
                  v.vleceny_let_id, coalesce(av.rejstrik, ak.rejstrik) AS vlek_rejstrik,
                  nullif(v.misto_vzletu, %(domovske)s) AS misto_vzletu,
                  nullif(v.misto_pristani, %(domovske)s) AS misto_pristani,
                  v.cas_vzletu, v.cas_pristani, v.doba_uctovana_min, v.pocet_pristani,
                  l.pob, a.max_doba_min, v.duvod_zruseni, v.zruseno, v.dodatecne, v.zalozeno,
                  (SELECT count(*) FROM lkkl.let_tg t WHERE t.let_id = v.id) AS pocet_tg,
                  coalesce((SELECT json_agg(json_build_object(
                                'jmeno', o.jmeno, 'prijmeni', o.prijmeni,
                                'funkce', f.nazev, 'funkce_kod', f.kod) ORDER BY f.poradi)
                            FROM lkkl.posadka p
                            JOIN lkkl.lov_osoba o ON o.id = p.osoba_id
                            JOIN lkkl.lov_funkce f ON f.id = p.funkce_id
                            WHERE p.let_id = v.id), '[]') AS posadka
           FROM lkkl.v_let v
           JOIN lkkl.let l ON l.id = v.id
           JOIN lkkl.lov_letadlo a ON a.id = v.letadlo_id
           LEFT JOIN lkkl.let lv ON lv.id = v.vlecny_let_id
           LEFT JOIN lkkl.lov_letadlo av ON av.id = lv.letadlo_id
           LEFT JOIN lkkl.let lk ON lk.id = v.vleceny_let_id
           LEFT JOIN lkkl.lov_letadlo ak ON ak.id = lk.letadlo_id
           WHERE v.den = %(den)s
              OR (v.stav = 'VE_VZDUCHU' AND %(den)s = (now() AT TIME ZONE 'UTC')::date)
           ORDER BY v.id""",
        {"den": den, "domovske": domovsky_kod},
    ).fetchall()
    te = slunce(domovske, den).te
    return LetyDne(ted=ted, lety=[Pasek(**r, varovani=varovani(r, ted, te)) for r in radky])
