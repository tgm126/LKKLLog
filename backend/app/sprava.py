"""Správa systému – jen admin (docs/modul-sprava.md): smazání letů celého dne a nastavení.

Mazání volá proceduru lkkl.smazat_lety_dne (db/033) – stejné pravidlo jako přímo v databázi;
audit zapíše, kdo mazal (kontext požadavku).
"""

from datetime import date

from fastapi import APIRouter, Depends
from psycopg import Connection

from .db import spojeni
from .model import Model
from .prihlasovani import Prihlaseny, admin

router = APIRouter(prefix="/api/sprava")


class DenSLety(Model):
    den: date
    lety: int


class SmazatDen(Model):
    den: date


class Smazano(Model):
    den: date
    smazano: int


class NastaveniSystemu(Model):
    testovaci_provoz: bool
    """Žlutý pruh TESTOVACÍ PROVOZ (db/034)."""


@router.get("/dny-s-lety", response_model=list[DenSLety])
def dny_s_lety(_: Prihlaseny = Depends(admin), conn: Connection = Depends(spojeni)):
    """Dny, kdy jsou nějaké lety (den letu jako v v_let), s počtem letů."""
    return conn.execute(
        "SELECT den, count(*)::int AS lety FROM lkkl.v_let GROUP BY den ORDER BY den"
    ).fetchall()


@router.post("/smazat-den", response_model=Smazano)
def smazat_den(
    data: SmazatDen, _: Prihlaseny = Depends(admin), conn: Connection = Depends(spojeni)
):
    with conn.transaction():
        r = conn.execute("CALL lkkl.smazat_lety_dne(%s)", (data.den,)).fetchone()
    return Smazano(den=data.den, smazano=r["smazano"])


@router.get("/nastaveni", response_model=NastaveniSystemu)
def nastaveni(_: Prihlaseny = Depends(admin), conn: Connection = Depends(spojeni)):
    return conn.execute("SELECT testovaci_provoz FROM lkkl.nastaveni").fetchone()


@router.post("/nastaveni", response_model=NastaveniSystemu)
def zmenit_nastaveni(
    data: NastaveniSystemu, _: Prihlaseny = Depends(admin), conn: Connection = Depends(spojeni)
):
    return conn.execute(
        "UPDATE lkkl.nastaveni SET testovaci_provoz = %s RETURNING testovaci_provoz",
        (data.testovaci_provoz,),
    ).fetchone()
