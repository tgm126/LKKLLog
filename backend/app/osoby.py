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
    spravuje_letadla: bool
    zablokovano: bool
    ma_heslo: bool


class OpravneniOsoby(BaseModel):
    """Oprávnění, které osoba má: pro které kategorie letadel a zda omezené."""

    id: int
    omezene: bool
    kategorie: list[int]


class Osoba(BaseModel):
    id: int
    jmeno: str
    prijmeni: str
    email: str | None
    telefon: str | None
    cislo_clena: str | None
    clen: bool
    platny: bool
    ucet: UcetOsoby | None
    opravneni: list[OpravneniOsoby]


class Kategorie(BaseModel):
    id: int
    nazev: str


class Opravneni(BaseModel):
    """Druh oprávnění z číselníku a kategorie, pro které se smí vydat."""

    id: int
    nazev: str
    lze_omezit: bool
    """Dává roli instruktora – jen tam má smysl „omezený“ (pod dohledem)."""
    kategorie: list[Kategorie]


class Seznam(BaseModel):
    osoby: list[Osoba]
    opravneni: list[Opravneni]


class Zmena(BaseModel):
    kdy: datetime
    kdo: str
    akce: str
    popis: str | None


class PosledniEmail(BaseModel):
    """Poslední e-mail osobě (lkkl.email, db/038); chyba prázdná = odesláno."""

    kdy: datetime
    adresa: str
    chyba: str | None


class DetailOsoby(Osoba):
    heslo_zmeneno: datetime | None
    pozvanka_odeslana: datetime | None
    posledni_prihlaseni: datetime | None
    posledni_email: PosledniEmail | None
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
    platny: bool | None = None

    @field_validator("jmeno", "prijmeni", "email", "cislo_clena")
    @classmethod
    def _orezat(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None

    @field_validator("telefon")
    @classmethod
    def _upravit_telefon(cls, v: str | None) -> str | None:
        return _telefon(v.strip()) if v is not None else None


class OpravneniIn(BaseModel):
    """Oprávnění pro kategorii: přidat (první kategorie oprávnění přidá) nebo odebrat
    (s poslední kategorií se odebere i oprávnění)."""

    opravneni_id: int
    kategorie_id: int
    ma: bool


class OmezeniIn(BaseModel):
    opravneni_id: int
    omezene: bool


# --- dotazy ----------------------------------------------------------------------------------

_OSOBA_SQL = """
SELECT o.id, o.jmeno, o.prijmeni, o.email, o.telefon, o.cislo_clena, o.clen, o.platny,
       CASE WHEN u.osoba_id IS NOT NULL THEN json_build_object(
           'smi_se_prihlasit', u.aktivni AND o.platny,
           'aktivni', u.aktivni,
           'admin', u.admin,
           'smi_odblokovat', u.smi_odblokovat,
           'spravuje_osoby', u.spravuje_osoby,
           'spravuje_letadla', u.spravuje_letadla,
           'zablokovano', coalesce(u.zablokovano_do > now(), false),
           'ma_heslo', u.heslo_hash IS NOT NULL) END AS ucet,
       coalesce((SELECT json_agg(json_build_object(
                     'id', oo.opravneni_id,
                     'omezene', oo.omezene,
                     'kategorie', (SELECT coalesce(json_agg(x.kategorie_id
                                                            ORDER BY x.kategorie_id), '[]')
                                   FROM lkkl.lov_osoba_opravneni_kategorie x
                                   WHERE x.osoba_id = oo.osoba_id
                                     AND x.opravneni_id = oo.opravneni_id)
                 ) ORDER BY oo.opravneni_id)
                 FROM lkkl.lov_osoba_opravneni oo WHERE oo.osoba_id = o.id),
                '[]') AS opravneni,
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
              OR (tabulka IN ('ucet', 'lov_osoba_opravneni', 'lov_osoba_opravneni_kategorie')
                  AND klic ->> 'osoba_id' = %(id)s)
           ORDER BY kdy DESC, id DESC
           LIMIT 50""",
        {"id": str(osoba_id)},
    ).fetchall()
    email = conn.execute(
        """SELECT kdy, adresa, chyba FROM lkkl.email WHERE osoba_id = %s
           ORDER BY kdy DESC, id DESC LIMIT 1""",
        (osoba_id,),
    ).fetchone()
    return DetailOsoby(**o, historie=historie, posledni_email=email)


# --- rozhraní ---------------------------------------------------------------------------------


@router.get("", response_model=Seznam)
def osoby(_: Prihlaseny = Depends(spravuje_osoby), conn: Connection = Depends(spojeni)):
    return {
        "osoby": conn.execute(_OSOBA_SQL + " ORDER BY o.prijmeni, o.jmeno").fetchall(),
        "opravneni": conn.execute(
            """SELECT o.id, o.nazev,
                      EXISTS (SELECT 1 FROM lkkl.lov_opravneni_role orl
                              JOIN lkkl.lov_role r ON r.id = orl.role_id
                              WHERE orl.opravneni_id = o.id AND r.kod = 'INSTRUKTOR') AS lze_omezit,
                      coalesce((SELECT json_agg(json_build_object('id', k.id, 'nazev', k.nazev)
                                                ORDER BY k.poradi, k.nazev)
                                FROM lkkl.lov_opravneni_kategorie ok
                                JOIN lkkl.v_lov_kategorie k ON k.id = ok.kategorie_id
                                WHERE ok.opravneni_id = o.id), '[]') AS kategorie
               FROM lkkl.v_lov_opravneni o"""
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
    if zmeny.get("platny") is False:
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
    k = {"osoba": osoba_id, "opravneni": data.opravneni_id, "kategorie": data.kategorie_id}
    try:
        with conn.transaction():
            if data.ma:
                conn.execute(
                    """INSERT INTO lkkl.lov_osoba_opravneni (osoba_id, opravneni_id)
                       VALUES (%(osoba)s, %(opravneni)s) ON CONFLICT DO NOTHING""",
                    k,
                )
                conn.execute(
                    """INSERT INTO lkkl.lov_osoba_opravneni_kategorie
                           (osoba_id, opravneni_id, kategorie_id)
                       VALUES (%(osoba)s, %(opravneni)s, %(kategorie)s) ON CONFLICT DO NOTHING""",
                    k,
                )
            else:
                conn.execute(
                    """DELETE FROM lkkl.lov_osoba_opravneni_kategorie
                       WHERE osoba_id = %(osoba)s AND opravneni_id = %(opravneni)s
                         AND kategorie_id = %(kategorie)s""",
                    k,
                )
                conn.execute(  # bez poslední kategorie osoba oprávnění nemá
                    """DELETE FROM lkkl.lov_osoba_opravneni oo
                       WHERE osoba_id = %(osoba)s AND opravneni_id = %(opravneni)s
                         AND NOT EXISTS (SELECT 1 FROM lkkl.lov_osoba_opravneni_kategorie x
                                         WHERE x.osoba_id = oo.osoba_id
                                           AND x.opravneni_id = oo.opravneni_id)""",
                    k,
                )
    except errors.ForeignKeyViolation as e:
        if e.diag.constraint_name == "kategorie_povolena":
            raise HTTPException(400, "Toto oprávnění se pro tuto kategorii nevydává.") from e
        raise HTTPException(404, "Osoba nebo oprávnění neexistuje.") from e
    return _detail(conn, osoba_id)


@router.post("/{osoba_id}/omezeni", response_model=DetailOsoby)
def osoba_omezeni(
    osoba_id: int,
    data: OmezeniIn,
    _: Prihlaseny = Depends(spravuje_osoby),
    conn: Connection = Depends(spojeni),
):
    """Omezený instruktor (pod dohledem) – vlastnost oprávnění, které osoba má."""
    upraveno = conn.execute(
        """UPDATE lkkl.lov_osoba_opravneni SET omezene = %s
           WHERE osoba_id = %s AND opravneni_id = %s RETURNING osoba_id""",
        (data.omezene, osoba_id, data.opravneni_id),
    ).fetchone()
    if upraveno is None:
        raise HTTPException(404, "Osoba toto oprávnění nemá.")
    return _detail(conn, osoba_id)
