"""Lety: přehled dne a sluneční časy (návrh: docs/modul-lety.md)."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from astral import Observer
from astral.sun import sun
from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection, errors
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


# --- akce letu: vzlet, přistání, T&G, zpět ---------------------------------------------------

PREKRYV = "Letadlo v tu dobu už letí – překrývá se s jiným letem."


@contextmanager
def zmena(conn: Connection) -> Iterator[None]:
    """Změna letu v jedné transakci; pravidla databáze (i odložená na konec transakce) se
    vyhodnotí hned a jejich chyba se vrátí jako srozumitelná hláška."""
    try:
        with conn.transaction():
            yield
            conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
    except errors.RaiseException as e:
        raise HTTPException(400, re.sub(r"^Let \d+: ", "", e.diag.message_primary or "")) from e
    except errors.ExclusionViolation as e:
        raise HTTPException(409, PREKRYV) from e


class Provedeno(BaseModel):
    """Výsledek akce pro oznámení se Zpět."""

    let_id: int
    rejstrik: str
    akce: str
    cas: datetime | None


def _let(conn: Connection, let_id: int) -> dict:
    let = conn.execute(
        "SELECT id, rejstrik, stav, cas_vzletu, cas_pristani FROM lkkl.v_let WHERE id = %s",
        (let_id,),
    ).fetchone()
    if let is None:
        raise HTTPException(404, "Let neexistuje.")
    return let


def _uz_provedeno(conn: Connection, let: dict, akce: str, cas: datetime | None) -> HTTPException:
    """409 s tím, kdo a kdy akci provedl (stisk platí jen jednou, i když tlačí víc lidí)."""
    if let["stav"] == "ZRUSEN":
        return HTTPException(409, f"{let['rejstrik']}: let je zrušený.")
    kdo = conn.execute(
        """SELECT kdo FROM lkkl.v_historie_letu WHERE let_id = %s AND akce = %s
           ORDER BY kdy DESC LIMIT 1""",
        (let["id"], akce),
    ).fetchone()
    kdy = f" v {cas:%H:%M:%S}" if cas else ""
    od = f" ({kdo['kdo']})" if kdo else ""
    sloveso = {"Vzlet": "Už vzlétl", "Přistání": "Už přistál"}[akce]
    return HTTPException(409, f"{let['rejstrik']}: {sloveso}{kdy}{od}.")


# Vzlet a jeho Zpět se týkají celé dvojice vleku (kluzák a vlečná startují společně).
DVOJICE = """SELECT %(id)s::bigint AS id
             UNION SELECT vlecny_let_id FROM lkkl.let
                   WHERE id = %(id)s AND vlecny_let_id IS NOT NULL
             UNION SELECT id FROM lkkl.let WHERE vlecny_let_id = %(id)s"""


@router.post("/lety/{let_id}/vzlet", response_model=Provedeno)
def vzlet(let_id: int, _: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)):
    let = _let(conn, let_id)
    with zmena(conn):
        cas = conn.execute(
            f"""UPDATE lkkl.let SET cas_vzletu = now()
                WHERE id IN ({DVOJICE}) AND cas_vzletu IS NULL AND zruseni_duvod_id IS NULL
                RETURNING cas_vzletu""",  # noqa: S608 – pevný text
            {"id": let_id},
        ).fetchone()
    if cas is None:
        raise _uz_provedeno(conn, let, "Vzlet", let["cas_vzletu"])
    return Provedeno(let_id=let_id, rejstrik=let["rejstrik"], akce="vzlet", cas=cas["cas_vzletu"])


@router.post("/lety/{let_id}/pristani", response_model=Provedeno)
def pristani(let_id: int, _: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)):
    """Přistání teď; místo = domovské (doplní databáze), přistání celkem = T&G + 1."""
    let = _let(conn, let_id)
    with zmena(conn):
        cas = conn.execute(
            """UPDATE lkkl.let l
               SET cas_pristani = now(),
                   pocet_pristani = (SELECT count(*) FROM lkkl.let_tg t WHERE t.let_id = l.id) + 1
               WHERE id = %s AND cas_vzletu IS NOT NULL AND cas_pristani IS NULL
                 AND zruseni_duvod_id IS NULL
               RETURNING cas_pristani""",
            (let_id,),
        ).fetchone()
    if cas is None:
        if let["stav"] == "NAPLANOVAN":
            raise HTTPException(409, f"{let['rejstrik']}: ještě nevzlétl.")
        raise _uz_provedeno(conn, let, "Přistání", let["cas_pristani"])
    return Provedeno(
        let_id=let_id, rejstrik=let["rejstrik"], akce="pristani", cas=cas["cas_pristani"]
    )


@router.post("/lety/{let_id}/tg", response_model=Provedeno)
def tg(let_id: int, _: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)):
    """Dotek a vzlet (touch and go) teď – jen motorová letadla, TMG a UL ve vzduchu."""
    let = _let(conn, let_id)
    with zmena(conn):
        cas = conn.execute(
            """INSERT INTO lkkl.let_tg (let_id, cas)
               SELECT v.id, now() FROM lkkl.v_let v
               WHERE v.id = %s AND v.stav = 'VE_VZDUCHU' AND v.kategorie_kod <> 'KLUZAK'
               RETURNING cas""",
            (let_id,),
        ).fetchone()
    if cas is None:
        raise HTTPException(409, f"{let['rejstrik']}: T&G jde jen u motorového letadla ve vzduchu.")
    return Provedeno(let_id=let_id, rejstrik=let["rejstrik"], akce="tg", cas=cas["cas"])


class ZpetIn(BaseModel):
    akce: Literal["vzlet", "pristani", "tg"]


ZPET_DO = timedelta(minutes=1)
"""Zpět nabízí obrazovka 6 s po akci; server dá rezervu na pomalé spojení."""


@router.post("/lety/{let_id}/zpet", response_model=Provedeno)
def zpet(
    let_id: int,
    data: ZpetIn,
    _: Prihlaseny = Depends(prihlaseny),
    conn: Connection = Depends(spojeni),
):
    """Vrátí poslední akci: vzlet → naplánovaný, přistání → ve vzduchu, T&G → bez posledního."""
    let = _let(conn, let_id)
    with zmena(conn):
        if data.akce == "vzlet":
            radky = conn.execute(
                f"""UPDATE lkkl.let SET cas_vzletu = NULL
                    WHERE id IN ({DVOJICE}) AND cas_pristani IS NULL
                      AND cas_vzletu > now() - %(do)s""",  # noqa: S608 – pevný text
                {"id": let_id, "do": ZPET_DO},
            ).rowcount
        elif data.akce == "pristani":
            radky = conn.execute(
                """UPDATE lkkl.let
                   SET cas_pristani = NULL, misto_pristani_id = NULL,
                       misto_pristani_popis = NULL, pocet_pristani = NULL
                   WHERE id = %s AND cas_pristani > now() - %s""",
                (let_id, ZPET_DO),
            ).rowcount
        else:
            radky = conn.execute(
                """DELETE FROM lkkl.let_tg
                   WHERE let_id = %(id)s AND cas > now() - %(do)s
                     AND cas = (SELECT max(cas) FROM lkkl.let_tg WHERE let_id = %(id)s)""",
                {"id": let_id, "do": ZPET_DO},
            ).rowcount
    if not radky:
        raise HTTPException(409, f"{let['rejstrik']}: vrátit už nejde.")
    return Provedeno(let_id=let_id, rejstrik=let["rejstrik"], akce=f"zpet_{data.akce}", cas=None)


# --- průvodce novým letem -------------------------------------------------------------------


@router.get("/lety/nabidky")
def nabidky(_: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)):
    """Vše pro průvodce novým letem v jednom dotazu (nabídky z pohledů v_lov_*)."""
    letadla = conn.execute(
        """SELECT a.id, a.rejstrik, a.typ, a.kategorie, a.kategorie_kod, a.pocet_mist,
                  a.vlecne, a.soukrome, a.mimo_provoz,
                  (SELECT min(v.cas_vzletu) FROM lkkl.v_let v
                   WHERE v.letadlo_id = a.id AND v.stav = 'VE_VZDUCHU') AS leti_od,
                  EXISTS (SELECT 1 FROM lkkl.v_let v
                          WHERE v.letadlo_id = a.id AND v.stav = 'NAPLANOVAN'
                            AND v.den = (now() AT TIME ZONE 'UTC')::date) AS naplanovan,
                  -- naposledy létající na letadle (rychlá volba osoby)
                  coalesce((SELECT array_agg(x.osoba_id ORDER BY x.naposledy DESC)
                            FROM (SELECT p.osoba_id, max(l.zalozeno) AS naposledy
                                  FROM lkkl.posadka p JOIN lkkl.let l ON l.id = p.let_id
                                  WHERE l.letadlo_id = a.id AND l.zruseni_duvod_id IS NULL
                                  GROUP BY p.osoba_id ORDER BY naposledy DESC LIMIT 5) x),
                           '{}') AS nedavni,
                  -- vlekař posledního vleku této vlečné
                  (SELECT p.osoba_id FROM lkkl.let l
                   JOIN lkkl.posadka p ON p.let_id = l.id
                   JOIN lkkl.lov_funkce f ON f.id = p.funkce_id AND f.kod = 'PIC'
                   WHERE l.letadlo_id = a.id
                     AND EXISTS (SELECT 1 FROM lkkl.let k WHERE k.vlecny_let_id = l.id)
                   ORDER BY l.zalozeno DESC LIMIT 1) AS posledni_vlekar
           FROM lkkl.v_lov_letadlo a"""
    ).fetchall()
    ucely = conn.execute(
        """SELECT u.id, u.kod, u.nazev, lu.uloha_povinna,
                  coalesce(json_agg(json_build_object('id', f.id, 'kod', f.kod, 'nazev', f.nazev,
                                                      'na_palube', f.na_palube)
                                    ORDER BY f.poradi) FILTER (WHERE f.id IS NOT NULL),
                           '[]') AS funkce
           FROM lkkl.v_lov_ucel u
           JOIN lkkl.lov_ucel lu ON lu.id = u.id
           LEFT JOIN lkkl.lov_ucel_funkce uf ON uf.ucel_id = u.id
           LEFT JOIN lkkl.lov_funkce f ON f.id = uf.funkce_id
           GROUP BY u.id, u.kod, u.nazev, u.poradi, lu.uloha_povinna
           ORDER BY u.poradi, u.nazev"""
    ).fetchall()
    return {
        "letadla": letadla,
        "ucely": ucely,
        "pic_id": conn.execute("SELECT id FROM lkkl.lov_funkce WHERE kod = 'PIC'").fetchone()["id"],
        "zpusoby": conn.execute("SELECT id, kod, nazev FROM lkkl.v_lov_zpusob_vzletu").fetchall(),
        "osoby": conn.execute(
            """SELECT id, jmeno, prijmeni, vlekar FROM lkkl.lov_osoba
               WHERE aktivni ORDER BY prijmeni, jmeno"""
        ).fetchall(),
        "ulohy": conn.execute(
            """SELECT u.id, u.nazev, u.osnova_id, u.osnova, u.ucel_id, k.kod AS kategorie_kod
               FROM lkkl.v_uloha_nabidka u
               LEFT JOIN lkkl.lov_kategorie k ON k.id = u.kategorie_id"""
        ).fetchall(),
        # jak se dnes naposledy vzlétalo s kluzákem (výchozí volba naviják / aerovlek)
        "zpusob_kluzaku": (
            conn.execute(
                """SELECT zpusob_vzletu_kod AS kod FROM lkkl.v_let
                   WHERE den = (now() AT TIME ZONE 'UTC')::date AND kategorie_kod = 'KLUZAK'
                     AND cas_vzletu IS NOT NULL
                   ORDER BY cas_vzletu DESC LIMIT 1"""
            ).fetchone()
            or {"kod": None}
        )["kod"],
    }


class ClenIn(BaseModel):
    osoba_id: int
    funkce_id: int


class NovyLet(BaseModel):
    letadlo_id: int
    ucel_id: int
    posadka: list[ClenIn]
    pob: int | None = None
    zpusob_vzletu_id: int
    vlecna_id: int | None = None
    """Aerovlek: letadlo vlečné (vlečný let se založí spolu s letem kluzáku)."""
    vlekar_id: int | None = None
    uloha_id: int | None = None
    platce_id: int | None = None
    """Prázdné a ne aeroklub = podle posádky (žák / přezkoušený, jinak PIC)."""
    plati_aeroklub: bool = False
    akce: Literal["vzlet", "naplanovat", "probehly"]
    cas_vzletu: datetime | None = None
    cas_pristani: datetime | None = None
    pocet_pristani: int = 1
    cas_pristani_vlecne: datetime | None = None
    """Proběhlý aerovlek: kdy přistála vlečná."""


def _zalozit(conn: Connection, udaje: dict, posadka: list[ClenIn]) -> int:
    let_id = conn.execute(
        """INSERT INTO lkkl.let (letadlo_id, ucel_id, zpusob_vzletu_id, vlecny_let_id,
               cas_vzletu, cas_pristani, pocet_pristani, pob, platce_id, plati_aeroklub,
               uloha_id, zalozil_id)
           VALUES (%(letadlo_id)s, %(ucel_id)s, %(zpusob_vzletu_id)s, %(vlecny_let_id)s,
                   CASE WHEN %(ted)s THEN now() ELSE %(cas_vzletu)s END, %(cas_pristani)s,
                   CASE WHEN %(cas_pristani)s::timestamptz IS NOT NULL
                        THEN %(pocet_pristani)s END,
                   %(pob)s, %(platce_id)s, %(plati_aeroklub)s, %(uloha_id)s, %(zalozil_id)s)
           RETURNING id""",
        udaje,
    ).fetchone()["id"]
    for c in posadka:
        conn.execute(
            "INSERT INTO lkkl.posadka (let_id, osoba_id, funkce_id) VALUES (%s, %s, %s)",
            (let_id, c.osoba_id, c.funkce_id),
        )
    return let_id


def _vychozi_platce(conn: Connection, posadka: list[ClenIn], pic_id: int) -> int | None:
    """Kdo je na palubě s jinou funkcí než PIC (žák, přezkoušený), jinak PIC."""
    jine = {
        r["id"]
        for r in conn.execute(
            "SELECT id FROM lkkl.lov_funkce WHERE na_palube AND kod <> 'PIC'"
        ).fetchall()
    }
    kandidati = [c for c in posadka if c.funkce_id in jine] or [
        c for c in posadka if c.funkce_id == pic_id
    ]
    return kandidati[0].osoba_id if kandidati else None


@router.post("/lety", response_model=Provedeno)
def novy_let(
    data: NovyLet, p: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)
):
    """Nový let z průvodce: vzlet teď, naplánovat, nebo proběhlý let; aerovlek jako dvojice."""
    probehly = data.akce == "probehly"
    if data.vlecna_id is not None and data.vlekar_id is None:
        raise HTTPException(400, "U aerovleku chybí vlekař.")
    if data.vlekar_id in {c.osoba_id for c in data.posadka}:
        raise HTTPException(400, "Vlekař nemůže být zároveň v posádce kluzáku.")
    if probehly:
        casy = [data.cas_vzletu, data.cas_pristani]
        if data.vlecna_id is not None:
            casy.append(data.cas_pristani_vlecne)
        if any(c is None for c in casy):
            raise HTTPException(400, "Chybí čas vzletu nebo přistání.")
        ted = conn.execute("SELECT now() AS t").fetchone()["t"]
        if any(c > ted for c in casy if c is not None):
            raise HTTPException(400, "Čas nesmí být v budoucnosti.")
    pic_id = conn.execute("SELECT id FROM lkkl.lov_funkce WHERE kod = 'PIC'").fetchone()["id"]
    platce_id = data.platce_id
    if platce_id is None and not data.plati_aeroklub:
        platce_id = _vychozi_platce(conn, data.posadka, pic_id)

    spolecne = {
        "ted": data.akce == "vzlet",
        "cas_vzletu": data.cas_vzletu if probehly else None,
        "platce_id": platce_id,
        "plati_aeroklub": data.plati_aeroklub,
        "zalozil_id": p.osoba_id,
    }
    with zmena(conn):
        vlecny_let_id = None
        if data.vlecna_id is not None and data.vlekar_id is not None:
            vlastni = conn.execute(
                "SELECT id FROM lkkl.lov_zpusob_vzletu WHERE kod = 'VLASTNI'"
            ).fetchone()["id"]
            vlecny_let_id = _zalozit(
                conn,
                {
                    **spolecne,
                    "letadlo_id": data.vlecna_id,
                    "ucel_id": None,
                    "zpusob_vzletu_id": vlastni,
                    "vlecny_let_id": None,
                    "cas_pristani": data.cas_pristani_vlecne if probehly else None,
                    "pocet_pristani": 1,
                    "pob": 1,
                    "uloha_id": None,
                },
                [ClenIn(osoba_id=data.vlekar_id, funkce_id=pic_id)],
            )
        let_id = _zalozit(
            conn,
            {
                **spolecne,
                "letadlo_id": data.letadlo_id,
                "ucel_id": data.ucel_id,
                "zpusob_vzletu_id": data.zpusob_vzletu_id,
                "vlecny_let_id": vlecny_let_id,
                "cas_pristani": data.cas_pristani if probehly else None,
                "pocet_pristani": data.pocet_pristani,
                "pob": data.pob,
                "uloha_id": data.uloha_id,
            },
            data.posadka,
        )
    let = _let(conn, let_id)
    return Provedeno(
        let_id=let_id,
        rejstrik=let["rejstrik"],
        akce=data.akce,
        cas=let["cas_vzletu"] if data.akce == "vzlet" else None,
    )
