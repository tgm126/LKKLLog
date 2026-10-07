"""Správa osob: seznam, detail, nová osoba, úpravy, oprávnění (návrh: docs/modul-osoby.md).

Smí správce osob a admin (prihlasovani.spravuje_osoby). Účty osob (založení, zablokování,
práva, odkaz pro heslo) obsluhují /api/ucty v prihlasovani.py.
"""

import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection, errors
from pydantic import BaseModel, field_validator

from .db import spojeni
from .prihlasovani import Prihlaseny, spravuje_osoby

router = APIRouter(prefix="/api/osoby")


# --- schémata -------------------------------------------------------------------------------


class UcetOsoby(BaseModel):
    smi_se_prihlasit: bool
    aktivni: bool
    admin: bool
    smi_odblokovat: bool
    spravuje_osoby: bool
    zablokovano: bool
    ma_heslo: bool


class Osoba(BaseModel):
    id: int
    jmeno: str
    prijmeni: str
    email: str | None
    telefon: str | None
    cislo_clena: str | None
    clen: bool
    aktivni: bool
    ucet: UcetOsoby | None
    opravneni: list[int]


class Opravneni(BaseModel):
    id: int
    nazev: str
    omezene: bool
    kategorie: list[str]
    """Názvy kategorií letadel; prázdné = všechna letadla."""


class Seznam(BaseModel):
    osoby: list[Osoba]
    opravneni: list[Opravneni]


class Zmena(BaseModel):
    kdy: datetime
    kdo: str
    akce: str
    popis: str | None


class DetailOsoby(Osoba):
    heslo_zmeneno: datetime | None
    pozvanka_odeslana: datetime | None
    posledni_prihlaseni: datetime | None
    historie: list[Zmena]


def _telefon(hodnota: str | None) -> str | None:
    """„602 123 456“, „00420…“ → „+420602123456“; jiný tvar nechá na kontrole v databázi."""
    if hodnota is None:
        return None
    cislo = re.sub(r"[\s\-/().]", "", hodnota)
    if cislo.startswith("00"):
        cislo = "+" + cislo[2:]
    if re.fullmatch(r"\d{9}", cislo):
        cislo = "+420" + cislo
    return cislo or None


class OsobaIn(BaseModel):
    """Údaje osoby; při úpravě se mění jen poslané (prázdný text = smazat)."""

    jmeno: str | None = None
    prijmeni: str | None = None
    email: str | None = None
    telefon: str | None = None
    cislo_clena: str | None = None
    clen: bool | None = None
    aktivni: bool | None = None

    @field_validator("jmeno", "prijmeni", "email", "cislo_clena")
    @classmethod
    def _orezat(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None

    @field_validator("telefon")
    @classmethod
    def _upravit_telefon(cls, v: str | None) -> str | None:
        return _telefon(v.strip()) if v is not None else None


class OpravneniIn(BaseModel):
    opravneni_id: int
    ma: bool


# --- dotazy ----------------------------------------------------------------------------------

_OSOBA_SQL = """
SELECT o.id, o.jmeno, o.prijmeni, o.email, o.telefon, o.cislo_clena, o.clen, o.aktivni,
       CASE WHEN u.osoba_id IS NOT NULL THEN json_build_object(
           'smi_se_prihlasit', u.aktivni AND o.aktivni,
           'aktivni', u.aktivni,
           'admin', u.admin,
           'smi_odblokovat', u.smi_odblokovat,
           'spravuje_osoby', u.spravuje_osoby,
           'zablokovano', coalesce(u.zablokovano_do > now(), false),
           'ma_heslo', u.heslo_hash IS NOT NULL) END AS ucet,
       coalesce((SELECT array_agg(oo.opravneni_id ORDER BY oo.opravneni_id)
                 FROM lkkl.lov_osoba_opravneni oo WHERE oo.osoba_id = o.id),
                '{}'::bigint[]) AS opravneni,
       u.heslo_zmeneno, u.pozvanka_odeslana, u.posledni_prihlaseni
FROM lkkl.lov_osoba o
LEFT JOIN lkkl.ucet u ON u.osoba_id = o.id
"""

# Čitelné hlášky k omezením lov_osoba (db/004, 017).
_CHYBY = {
    "lov_osoba_email_check": "Neplatný e-mail.",
    "lov_osoba_telefon_check": "Telefon zadejte s předvolbou, např. +420 602 123 456.",
    "lov_osoba_cislo_clena_check": "Číslo člena smí obsahovat jen číslice.",
    "cislo_jen_u_clena": "Číslo člena má jen člen klubu.",
    "lov_osoba_jmeno_check": "Jméno musí být vyplněné.",
    "lov_osoba_prijmeni_check": "Příjmení musí být vyplněné.",
    "lov_osoba_email_jedinecny": "Tento e-mail už má jiná osoba.",
    "lov_osoba_cislo_clena_key": "Toto číslo člena už má jiná osoba.",
}


def _chyba(e: errors.Error) -> HTTPException:
    if isinstance(e, errors.RaiseException):
        return HTTPException(400, e.diag.message_primary)
    return HTTPException(400, _CHYBY.get(e.diag.constraint_name or "", "Údaje nejdou uložit."))


def _detail(conn: Connection, osoba_id: int) -> DetailOsoby:
    o = conn.execute(_OSOBA_SQL + " WHERE o.id = %s", (osoba_id,)).fetchone()
    if o is None:
        raise HTTPException(404, "Osoba neexistuje.")
    historie = conn.execute(
        """SELECT kdy, kdo, akce, popis FROM lkkl.v_audit
           WHERE (tabulka = 'lov_osoba' AND klic ->> 'id' = %(id)s)
              OR (tabulka IN ('ucet', 'lov_osoba_opravneni') AND klic ->> 'osoba_id' = %(id)s)
           ORDER BY kdy DESC, id DESC
           LIMIT 50""",
        {"id": str(osoba_id)},
    ).fetchall()
    return DetailOsoby(**o, historie=historie)


# --- rozhraní ---------------------------------------------------------------------------------


@router.get("", response_model=Seznam)
def osoby(_: Prihlaseny = Depends(spravuje_osoby), conn: Connection = Depends(spojeni)):
    return {
        "osoby": conn.execute(_OSOBA_SQL + " ORDER BY o.prijmeni, o.jmeno").fetchall(),
        "opravneni": conn.execute(
            """SELECT o.id, o.nazev, o.omezene,
                      coalesce(array_agg(k.nazev::text ORDER BY k.poradi)
                               FILTER (WHERE k.id IS NOT NULL), '{}'::text[]) AS kategorie
               FROM lkkl.v_lov_opravneni o
               LEFT JOIN lkkl.lov_opravneni_kategorie ok ON ok.opravneni_id = o.id
               LEFT JOIN lkkl.lov_kategorie k ON k.id = ok.kategorie_id
               GROUP BY o.id, o.nazev, o.omezene, o.poradi
               ORDER BY o.poradi, o.nazev"""
        ).fetchall(),
    }


@router.get("/{osoba_id}", response_model=DetailOsoby)
def osoba(
    osoba_id: int, _: Prihlaseny = Depends(spravuje_osoby), conn: Connection = Depends(spojeni)
):
    return _detail(conn, osoba_id)


@router.post("", response_model=DetailOsoby)
def osoba_zalozit(
    data: OsobaIn, _: Prihlaseny = Depends(spravuje_osoby), conn: Connection = Depends(spojeni)
):
    try:
        with conn.transaction():
            osoba_id = conn.execute(
                """INSERT INTO lkkl.lov_osoba (jmeno, prijmeni, email, telefon, cislo_clena, clen)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (
                    data.jmeno or "",
                    data.prijmeni or "",
                    data.email or None,
                    data.telefon,
                    data.cislo_clena or None,
                    True if data.clen is None else data.clen,
                ),
            ).fetchone()["id"]
    except (errors.CheckViolation, errors.UniqueViolation, errors.RaiseException) as e:
        raise _chyba(e) from e
    return _detail(conn, osoba_id)


@router.post("/{osoba_id}", response_model=DetailOsoby)
def osoba_zmenit(
    osoba_id: int,
    data: OsobaIn,
    p: Prihlaseny = Depends(spravuje_osoby),
    conn: Connection = Depends(spojeni),
):
    zmeny = {k: getattr(data, k) for k in data.model_fields_set}
    for k in ("email", "cislo_clena"):  # prázdný text = smazat
        if k in zmeny and not zmeny[k]:
            zmeny[k] = None
    if zmeny.get("aktivni") is False:
        if osoba_id == p.osoba_id:
            raise HTTPException(400, "Sám sebe nemůžete vypnout.")
        admin = conn.execute(
            "SELECT admin FROM lkkl.ucet WHERE osoba_id = %s", (osoba_id,)
        ).fetchone()
        if admin and admin["admin"] and not p.admin:
            raise HTTPException(403, "Admina smí vypnout jen admin.")
    if zmeny:
        sloupce = ", ".join(f"{k} = %({k})s" for k in zmeny)  # jen názvy z OsobaIn
        try:
            with conn.transaction():
                upraveno = conn.execute(
                    f"UPDATE lkkl.lov_osoba SET {sloupce} WHERE id = %(id)s RETURNING id",  # noqa: S608
                    {**zmeny, "id": osoba_id},
                ).fetchone()
        except (errors.CheckViolation, errors.UniqueViolation, errors.RaiseException) as e:
            raise _chyba(e) from e
        if upraveno is None:
            raise HTTPException(404, "Osoba neexistuje.")
    return _detail(conn, osoba_id)


@router.post("/{osoba_id}/opravneni", response_model=DetailOsoby)
def osoba_opravneni(
    osoba_id: int,
    data: OpravneniIn,
    _: Prihlaseny = Depends(spravuje_osoby),
    conn: Connection = Depends(spojeni),
):
    try:
        if data.ma:
            conn.execute(
                """INSERT INTO lkkl.lov_osoba_opravneni (osoba_id, opravneni_id) VALUES (%s, %s)
                   ON CONFLICT DO NOTHING""",
                (osoba_id, data.opravneni_id),
            )
        else:
            conn.execute(
                "DELETE FROM lkkl.lov_osoba_opravneni WHERE osoba_id = %s AND opravneni_id = %s",
                (osoba_id, data.opravneni_id),
            )
    except errors.ForeignKeyViolation as e:
        raise HTTPException(404, "Osoba nebo oprávnění neexistuje.") from e
    return _detail(conn, osoba_id)
