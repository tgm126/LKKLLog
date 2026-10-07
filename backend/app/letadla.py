"""Letadla: seznam a přepínač mimo provoz (návrh: docs/modul-letadla.md).

Smí správce letadel a admin (prihlasovani.spravuje_letadla). Změnu zachytí audit (db/012).
"""

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection
from pydantic import BaseModel

from .db import spojeni
from .prihlasovani import Prihlaseny, spravuje_letadla

router = APIRouter(prefix="/api/letadla")


class Letadlo(BaseModel):
    id: int
    rejstrik: str
    typ: str
    kategorie: str
    soukrome: bool
    mimo_provoz: bool


class MimoProvozIn(BaseModel):
    mimo_provoz: bool


_LETADLA_SQL = """SELECT id, rejstrik, typ, kategorie, soukrome, mimo_provoz
                  FROM lkkl.v_lov_letadlo"""


@router.get("", response_model=list[Letadlo])
def letadla(_: Prihlaseny = Depends(spravuje_letadla), conn: Connection = Depends(spojeni)):
    """Všechna letadla po kategoriích a typech (pořadí z pohledu)."""
    return conn.execute(_LETADLA_SQL).fetchall()


@router.post("/{letadlo_id}/mimo-provoz", response_model=Letadlo)
def mimo_provoz(
    letadlo_id: int,
    data: MimoProvozIn,
    _: Prihlaseny = Depends(spravuje_letadla),
    conn: Connection = Depends(spojeni),
):
    """Mimo provoz = nenabízí se pro nové lety; stará data zůstávají."""
    zmeneno = conn.execute(
        "UPDATE lkkl.lov_letadlo SET mimo_provoz = %s WHERE id = %s RETURNING id",
        (data.mimo_provoz, letadlo_id),
    ).fetchone()
    if zmeneno is None:
        raise HTTPException(404, "Letadlo neexistuje.")
    return conn.execute(_LETADLA_SQL + " WHERE id = %s", (letadlo_id,)).fetchone()
