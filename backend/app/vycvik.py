"""Editor výcviku (desktop): osnovy, úlohy a typy přezkoušení – docs/modul-osnovy.md.

Smí admin a správce výcviku (prihlasovani.spravuje_vycvik). Pravidla, která by rozbila staré
lety (kategorie, účel, oprávnění pro kategorii), hlídá databáze (db/042, vycvik_kontrola);
server jejich chybu vrátí jako hlášku. Každá změna vrátí celý stav editoru. Změny zapisuje
audit (db/042) – kromě pořadí.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection, errors
from pydantic import BaseModel

from . import db
from .db import spojeni
from .prihlasovani import Prihlaseny, spravuje_vycvik

router = APIRouter(prefix="/api/vycvik")


# --- schémata -------------------------------------------------------------------------------


class Ucel(BaseModel):
    id: int
    kod: str
    nazev: str
    uloha_povinna: bool


class Kategorie(BaseModel):
    id: int
    kod: str
    nazev: str


class Uloha(BaseModel):
    id: int
    kod: str
    nazev: str
    platny: bool
    ucely: list[int]
    lety: int


class Osnova(BaseModel):
    id: int
    kod: str
    nazev: str
    kategorie_id: int
    platny: bool
    ulohy: list[Uloha]


class Typ(BaseModel):
    """Typ přezkoušení s oprávněními, která ho smí provést."""

    id: int
    kod: str
    nazev: str
    kategorie_id: int
    platny: bool
    opravneni: list[int]
    lety: int


class Opravneni(BaseModel):
    id: int
    nazev: str
    kategorie: list[int]
    """Kategorie, pro které se oprávnění vydává."""


class Examinator(BaseModel):
    osoba_id: int
    jmeno: str
    prijmeni: str
    prezkouseni: list[int]
    """Typy přezkoušení, které smí provést (v_osoba_prezkouseni)."""


class Vycvik(BaseModel):
    ucely: list[Ucel]
    kategorie: list[Kategorie]
    osnovy: list[Osnova]
    typy: list[Typ]
    opravneni: list[Opravneni]
    examinatori: list[Examinator]


class NovaOsnova(BaseModel):
    kod: str
    nazev: str
    kategorie_id: int


class ZmenaOsnovy(BaseModel):
    kod: str | None = None
    nazev: str | None = None
    kategorie_id: int | None = None
    platny: bool | None = None


class NovaUloha(BaseModel):
    osnova_id: int
    kod: str
    nazev: str


class ZmenaUlohy(BaseModel):
    kod: str | None = None
    nazev: str | None = None
    osnova_id: int | None = None
    platny: bool | None = None


class NovyTyp(BaseModel):
    kod: str
    nazev: str
    kategorie_id: int


class ZmenaTypu(BaseModel):
    kod: str | None = None
    nazev: str | None = None
    kategorie_id: int | None = None
    platny: bool | None = None


class Vazba(BaseModel):
    """Zaškrtnutí: účel u úlohy (osnovy) nebo oprávnění u typu přezkoušení."""

    id: int
    ano: bool


class Posun(BaseModel):
    co: Literal["osnova", "uloha", "typ"]
    id: int
    smer: Literal[-1, 1]


# --- stav editoru -----------------------------------------------------------------------------


def _stav(conn: Connection) -> dict:
    return {
        # účely, u kterých se úlohy nabízejí, i Přezkoušení (náhled nového letu)
        "ucely": conn.execute(
            """SELECT u.id, u.kod, u.nazev, l.uloha_povinna
               FROM lkkl.v_lov_ucel u JOIN lkkl.lov_ucel l ON l.id = u.id"""
        ).fetchall(),
        "kategorie": conn.execute("SELECT id, kod, nazev FROM lkkl.v_lov_kategorie").fetchall(),
        # i neplatné osnovy a úlohy (jdou vrátit); počet letů = smazat jen nepoužité
        "osnovy": conn.execute(
            """SELECT o.id, o.kod, o.nazev, o.kategorie_id, o.platny,
                      coalesce((SELECT json_agg(json_build_object(
                                    'id', u.id, 'kod', u.kod, 'nazev', u.nazev,
                                    'platny', u.platny,
                                    'ucely', coalesce((SELECT json_agg(uu.ucel_id
                                                                       ORDER BY uu.ucel_id)
                                                       FROM lkkl.lov_uloha_ucel uu
                                                       WHERE uu.uloha_id = u.id), '[]'),
                                    'lety', (SELECT count(*) FROM lkkl.let l
                                             WHERE l.uloha_id = u.id))
                                    ORDER BY u.poradi, u.nazev)
                                FROM lkkl.lov_uloha u WHERE u.osnova_id = o.id), '[]') AS ulohy
               FROM lkkl.lov_osnova o
               ORDER BY o.poradi, o.nazev"""
        ).fetchall(),
        "typy": conn.execute(
            """SELECT p.id, p.kod, p.nazev, p.kategorie_id, p.platny,
                      coalesce((SELECT array_agg(po.opravneni_id ORDER BY po.opravneni_id)
                                FROM lkkl.lov_prezkouseni_opravneni po
                                WHERE po.prezkouseni_id = p.id), '{}'::bigint[]) AS opravneni,
                      (SELECT count(*) FROM lkkl.let l WHERE l.prezkouseni_id = p.id) AS lety
               FROM lkkl.lov_prezkouseni p
               ORDER BY p.poradi, p.nazev"""
        ).fetchall(),
        "opravneni": conn.execute(
            """SELECT o.id, o.nazev,
                      coalesce((SELECT array_agg(ok.kategorie_id ORDER BY ok.kategorie_id)
                                FROM lkkl.lov_opravneni_kategorie ok
                                WHERE ok.opravneni_id = o.id), '{}'::bigint[]) AS kategorie
               FROM lkkl.v_lov_opravneni o"""
        ).fetchall(),
        "examinatori": conn.execute(
            """SELECT o.id AS osoba_id, o.jmeno, o.prijmeni,
                      array_agg(s.prezkouseni_id ORDER BY s.prezkouseni_id) AS prezkouseni
               FROM lkkl.v_osoba_prezkouseni s
               JOIN lkkl.lov_osoba o ON o.id = s.osoba_id AND o.platny
               GROUP BY o.id ORDER BY o.prijmeni, o.jmeno"""
        ).fetchall(),
    }


# Hlášky k pravidlům databáze (domény lkkl.kod a lkkl.nazev, jedinečná označení, vazby).
HLASKY = {
    "kod_check": "Označení: jen velká písmena, číslice, podtržítko a pomlčka.",
    "nazev_check": "Název nesmí být prázdný.",
    errors.UniqueViolation: "Toto označení už existuje.",
}


def _zmena(conn: Connection):
    return db.transakce(conn, HLASKY)


def _upravit(conn: Connection, tabulka: str, id_: int, zmeny: dict) -> None:
    """UPDATE jen zadaných sloupců (názvy z pevných modelů), jinak 404."""
    if "kod" in zmeny:
        zmeny["kod"] = zmeny["kod"].strip().upper()
    if "nazev" in zmeny:
        zmeny["nazev"] = zmeny["nazev"].strip()
    if not db.upravit(conn, tabulka, id_, zmeny):
        raise HTTPException(404, "Záznam neexistuje.")


def _dalsi_poradi(conn: Connection, tabulka: str, kde: str = "true", hodnoty: tuple = ()) -> int:
    return conn.execute(
        f"SELECT coalesce(max(poradi), 0) + 10 AS p FROM lkkl.{tabulka} WHERE {kde}",  # noqa: S608
        hodnoty,
    ).fetchone()["p"]


# --- rozhraní ---------------------------------------------------------------------------------


@router.get("", response_model=Vycvik)
def vycvik(_: Prihlaseny = Depends(spravuje_vycvik), conn: Connection = Depends(spojeni)):
    return _stav(conn)


@router.post("/osnovy", response_model=Vycvik)
def nova_osnova(
    data: NovaOsnova, _: Prihlaseny = Depends(spravuje_vycvik), conn: Connection = Depends(spojeni)
):
    with _zmena(conn):
        conn.execute(
            """INSERT INTO lkkl.lov_osnova (kod, nazev, kategorie_id, poradi)
               VALUES (%s, %s, %s, %s)""",
            (
                data.kod.strip().upper(),
                data.nazev.strip(),
                data.kategorie_id,
                _dalsi_poradi(conn, "lov_osnova"),
            ),
        )
    return _stav(conn)


@router.post("/osnovy/{osnova_id}", response_model=Vycvik)
def zmenit_osnovu(
    osnova_id: int,
    data: ZmenaOsnovy,
    _: Prihlaseny = Depends(spravuje_vycvik),
    conn: Connection = Depends(spojeni),
):
    with _zmena(conn):
        _upravit(conn, "lov_osnova", osnova_id, data.model_dump(exclude_unset=True))
    return _stav(conn)


@router.post("/osnovy/{osnova_id}/smazat", response_model=Vycvik)
def smazat_osnovu(
    osnova_id: int, _: Prihlaseny = Depends(spravuje_vycvik), conn: Connection = Depends(spojeni)
):
    """Jen osnovu bez úloh (úlohy se nejdřív smažou nebo přesunou)."""
    if conn.execute("SELECT 1 FROM lkkl.lov_uloha WHERE osnova_id = %s", (osnova_id,)).fetchone():
        raise HTTPException(409, "Osnova má úlohy – smazat jde jen prázdnou, jinak zneplatnit.")
    with _zmena(conn):
        conn.execute("DELETE FROM lkkl.lov_osnova WHERE id = %s", (osnova_id,))
    return _stav(conn)


@router.post("/osnovy/{osnova_id}/ucel", response_model=Vycvik)
def ucel_osnovy(
    osnova_id: int,
    data: Vazba,
    _: Prihlaseny = Depends(spravuje_vycvik),
    conn: Connection = Depends(spojeni),
):
    """Souhrnné zaškrtávátko osnovy: účel všem jejím úlohám (nebo žádné)."""
    with _zmena(conn):
        if data.ano:
            conn.execute(
                """INSERT INTO lkkl.lov_uloha_ucel (uloha_id, ucel_id)
                   SELECT id, %s FROM lkkl.lov_uloha WHERE osnova_id = %s
                   ON CONFLICT DO NOTHING""",
                (data.id, osnova_id),
            )
        else:
            conn.execute(
                """DELETE FROM lkkl.lov_uloha_ucel
                   WHERE ucel_id = %s
                     AND uloha_id IN (SELECT id FROM lkkl.lov_uloha WHERE osnova_id = %s)""",
                (data.id, osnova_id),
            )
    return _stav(conn)


@router.post("/ulohy", response_model=Vycvik)
def nova_uloha(
    data: NovaUloha, _: Prihlaseny = Depends(spravuje_vycvik), conn: Connection = Depends(spojeni)
):
    with _zmena(conn):
        conn.execute(
            """INSERT INTO lkkl.lov_uloha (osnova_id, kod, nazev, poradi)
               VALUES (%s, %s, %s, %s)""",
            (
                data.osnova_id,
                data.kod.strip().upper(),
                data.nazev.strip(),
                _dalsi_poradi(conn, "lov_uloha", "osnova_id = %s", (data.osnova_id,)),
            ),
        )
    return _stav(conn)


@router.post("/ulohy/{uloha_id}", response_model=Vycvik)
def zmenit_ulohu(
    uloha_id: int,
    data: ZmenaUlohy,
    _: Prihlaseny = Depends(spravuje_vycvik),
    conn: Connection = Depends(spojeni),
):
    """Úprava úlohy; přesun do jiné osnovy ji zařadí na konec."""
    zmeny = data.model_dump(exclude_unset=True)
    with _zmena(conn):
        if zmeny.get("osnova_id") is not None:
            zmeny["poradi"] = _dalsi_poradi(
                conn, "lov_uloha", "osnova_id = %s", (zmeny["osnova_id"],)
            )
        _upravit(conn, "lov_uloha", uloha_id, zmeny)
    return _stav(conn)


@router.post("/ulohy/{uloha_id}/smazat", response_model=Vycvik)
def smazat_ulohu(
    uloha_id: int, _: Prihlaseny = Depends(spravuje_vycvik), conn: Connection = Depends(spojeni)
):
    """Jen úlohu bez letů (s jejími účely); použitou jen zneplatnit."""
    if conn.execute("SELECT 1 FROM lkkl.let WHERE uloha_id = %s", (uloha_id,)).fetchone():
        raise HTTPException(409, "Úloha je použita v letech – nejde smazat, jen zneplatnit.")
    with _zmena(conn):
        conn.execute("DELETE FROM lkkl.lov_uloha_ucel WHERE uloha_id = %s", (uloha_id,))
        conn.execute("DELETE FROM lkkl.lov_uloha WHERE id = %s", (uloha_id,))
    return _stav(conn)


@router.post("/ulohy/{uloha_id}/ucel", response_model=Vycvik)
def ucel_ulohy(
    uloha_id: int,
    data: Vazba,
    _: Prihlaseny = Depends(spravuje_vycvik),
    conn: Connection = Depends(spojeni),
):
    with _zmena(conn):
        if data.ano:
            conn.execute(
                """INSERT INTO lkkl.lov_uloha_ucel (uloha_id, ucel_id) VALUES (%s, %s)
                   ON CONFLICT DO NOTHING""",
                (uloha_id, data.id),
            )
        else:
            conn.execute(
                "DELETE FROM lkkl.lov_uloha_ucel WHERE uloha_id = %s AND ucel_id = %s",
                (uloha_id, data.id),
            )
    return _stav(conn)


@router.post("/typy", response_model=Vycvik)
def novy_typ(
    data: NovyTyp, _: Prihlaseny = Depends(spravuje_vycvik), conn: Connection = Depends(spojeni)
):
    with _zmena(conn):
        conn.execute(
            """INSERT INTO lkkl.lov_prezkouseni (kod, nazev, kategorie_id, poradi)
               VALUES (%s, %s, %s, %s)""",
            (
                data.kod.strip().upper(),
                data.nazev.strip(),
                data.kategorie_id,
                _dalsi_poradi(conn, "lov_prezkouseni", "kategorie_id = %s", (data.kategorie_id,)),
            ),
        )
    return _stav(conn)


@router.post("/typy/{typ_id}", response_model=Vycvik)
def zmenit_typ(
    typ_id: int,
    data: ZmenaTypu,
    _: Prihlaseny = Depends(spravuje_vycvik),
    conn: Connection = Depends(spojeni),
):
    """Úprava typu; při změně kategorie odpadnou oprávnění, která se pro ni nevydávají."""
    zmeny = data.model_dump(exclude_unset=True)
    with _zmena(conn):
        if zmeny.get("kategorie_id") is not None:
            if conn.execute(
                "SELECT 1 FROM lkkl.let WHERE prezkouseni_id = %s", (typ_id,)
            ).fetchone():
                raise HTTPException(400, "Typ je použit v letech – kategorii nejde změnit.")
            conn.execute(
                """DELETE FROM lkkl.lov_prezkouseni_opravneni po
                   WHERE po.prezkouseni_id = %(typ)s
                     AND NOT EXISTS (SELECT 1 FROM lkkl.lov_opravneni_kategorie ok
                                     WHERE ok.opravneni_id = po.opravneni_id
                                       AND ok.kategorie_id = %(kat)s)""",
                {"typ": typ_id, "kat": zmeny["kategorie_id"]},
            )
        _upravit(conn, "lov_prezkouseni", typ_id, zmeny)
    return _stav(conn)


@router.post("/typy/{typ_id}/smazat", response_model=Vycvik)
def smazat_typ(
    typ_id: int, _: Prihlaseny = Depends(spravuje_vycvik), conn: Connection = Depends(spojeni)
):
    """Jen typ bez letů (s jeho oprávněními); použitý jen zneplatnit."""
    if conn.execute("SELECT 1 FROM lkkl.let WHERE prezkouseni_id = %s", (typ_id,)).fetchone():
        raise HTTPException(409, "Typ je použit v letech – nejde smazat, jen zneplatnit.")
    with _zmena(conn):
        conn.execute(
            "DELETE FROM lkkl.lov_prezkouseni_opravneni WHERE prezkouseni_id = %s", (typ_id,)
        )
        conn.execute("DELETE FROM lkkl.lov_prezkouseni WHERE id = %s", (typ_id,))
    return _stav(conn)


@router.post("/typy/{typ_id}/opravneni", response_model=Vycvik)
def opravneni_typu(
    typ_id: int,
    data: Vazba,
    _: Prihlaseny = Depends(spravuje_vycvik),
    conn: Connection = Depends(spojeni),
):
    """Kdo smí typ provést: oprávnění (jen vydávané pro kategorii typu – hlídá databáze)."""
    with _zmena(conn):
        if data.ano:
            conn.execute(
                """INSERT INTO lkkl.lov_prezkouseni_opravneni (prezkouseni_id, opravneni_id)
                   VALUES (%s, %s) ON CONFLICT DO NOTHING""",
                (typ_id, data.id),
            )
        else:
            conn.execute(
                """DELETE FROM lkkl.lov_prezkouseni_opravneni
                   WHERE prezkouseni_id = %s AND opravneni_id = %s""",
                (typ_id, data.id),
            )
    return _stav(conn)


# Pořadí: sourozenci (všechny osnovy, úlohy osnovy, typy kategorie) se přečíslují po 10
# a vybraný se prohodí se sousedem.
_SOUROZENCI = {
    "osnova": ("lov_osnova", "true"),
    "uloha": ("lov_uloha", "osnova_id = (SELECT osnova_id FROM lkkl.lov_uloha WHERE id = %(id)s)"),
    "typ": (
        "lov_prezkouseni",
        "kategorie_id = (SELECT kategorie_id FROM lkkl.lov_prezkouseni WHERE id = %(id)s)",
    ),
}


@router.post("/posun", response_model=Vycvik)
def posun(
    data: Posun, _: Prihlaseny = Depends(spravuje_vycvik), conn: Connection = Depends(spojeni)
):
    tabulka, kde = _SOUROZENCI[data.co]
    with _zmena(conn):
        ids = [
            r["id"]
            for r in conn.execute(
                f"SELECT id FROM lkkl.{tabulka} WHERE {kde} ORDER BY poradi, nazev",  # noqa: S608
                {"id": data.id},
            ).fetchall()
        ]
        if data.id not in ids:
            raise HTTPException(404, "Záznam neexistuje.")
        i = ids.index(data.id)
        j = i + data.smer
        if 0 <= j < len(ids):
            ids[i], ids[j] = ids[j], ids[i]
            for k, id_ in enumerate(ids):
                conn.execute(
                    f"UPDATE lkkl.{tabulka} SET poradi = %s WHERE id = %s",  # noqa: S608
                    ((k + 1) * 10, id_),
                )
    return _stav(conn)
