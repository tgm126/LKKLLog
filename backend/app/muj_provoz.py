"""Můj provoz: letiště a osoby v provozu na dnešek, jen pro relaci (docs/modul-muj-provoz.md).

Nastavení platí jen pro den (UTC), kdy bylo uloženo – pravidlo drží pohledy v_relace_letiste
a v_relace_osoba (db/026); první uložení v novém dni přepíše staré nastavení.
"""

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection, errors
from pydantic import BaseModel

from .db import spojeni
from .lety import Letiste
from .prihlasovani import Prihlaseny, prihlaseny

router = APIRouter(prefix="/api/muj-provoz")


class MujProvoz(BaseModel):
    letiste: Letiste | None
    """Moje letiště na dnešek (zvolené, jinak domovské)."""
    osoby: list[int]
    """Osoby v provozu (filtr nabídky osob v posádce); prázdné = bez filtru."""


class LetisteIn(BaseModel):
    letiste_id: int | None
    """Prázdné = domovské."""


class OsobaIn(BaseModel):
    osoba_id: int
    ma: bool


def _muj_provoz(conn: Connection, relace_id: str) -> MujProvoz:
    letiste = conn.execute(
        """SELECT letiste_id AS id, kod, nazev, domovske
           FROM lkkl.v_relace_letiste WHERE relace_id = %s""",
        (relace_id,),
    ).fetchone()
    osoby = conn.execute(
        "SELECT osoba_id FROM lkkl.v_relace_osoba WHERE relace_id = %s ORDER BY osoba_id",
        (relace_id,),
    ).fetchall()
    return MujProvoz(letiste=letiste, osoby=[r["osoba_id"] for r in osoby])


def _dnesni(conn: Connection, relace_id: str) -> None:
    """Nastavení relace na dnešek; nastavení z jiného dne se zahodí (i osoby)."""
    conn.execute(
        """DELETE FROM lkkl.relace_provoz_osoba ro USING lkkl.relace_provoz rp
           WHERE rp.relace_id = ro.relace_id AND ro.relace_id = %s
             AND rp.den <> (now() AT TIME ZONE 'UTC')::date""",
        (relace_id,),
    )
    conn.execute(
        """INSERT INTO lkkl.relace_provoz (relace_id, den)
           VALUES (%s, (now() AT TIME ZONE 'UTC')::date)
           ON CONFLICT (relace_id) DO UPDATE
           SET den = excluded.den,
               letiste_id = CASE WHEN lkkl.relace_provoz.den = excluded.den
                                 THEN lkkl.relace_provoz.letiste_id END""",
        (relace_id,),
    )


@router.get("", response_model=MujProvoz)
def muj_provoz(p: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)):
    return _muj_provoz(conn, p.relace_id)


@router.post("/letiste", response_model=MujProvoz)
def letiste(
    data: LetisteIn, p: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)
):
    try:
        with conn.transaction():
            _dnesni(conn, p.relace_id)
            conn.execute(
                "UPDATE lkkl.relace_provoz SET letiste_id = %s WHERE relace_id = %s",
                (data.letiste_id, p.relace_id),
            )
    except errors.ForeignKeyViolation as e:
        raise HTTPException(404, "Letiště neexistuje.") from e
    return _muj_provoz(conn, p.relace_id)


@router.post("/osoby", response_model=MujProvoz)
def osoby(data: OsobaIn, p: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)):
    try:
        with conn.transaction():
            _dnesni(conn, p.relace_id)
            if data.ma:
                conn.execute(
                    """INSERT INTO lkkl.relace_provoz_osoba (relace_id, osoba_id)
                       VALUES (%s, %s) ON CONFLICT DO NOTHING""",
                    (p.relace_id, data.osoba_id),
                )
            else:
                conn.execute(
                    "DELETE FROM lkkl.relace_provoz_osoba WHERE relace_id = %s AND osoba_id = %s",
                    (p.relace_id, data.osoba_id),
                )
    except errors.ForeignKeyViolation as e:
        raise HTTPException(404, "Osoba neexistuje.") from e
    return _muj_provoz(conn, p.relace_id)


@router.post("/osoby/zrusit", response_model=MujProvoz)
def osoby_zrusit(p: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)):
    """Bez filtru – v posádce se zase nabízejí všichni."""
    conn.execute("DELETE FROM lkkl.relace_provoz_osoba WHERE relace_id = %s", (p.relace_id,))
    return _muj_provoz(conn, p.relace_id)
