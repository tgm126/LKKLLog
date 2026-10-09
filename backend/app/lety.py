"""Lety: přehled dne a sluneční časy (návrh: docs/modul-lety.md)."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from astral import Observer
from astral.sun import dawn, dusk, sun
from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection, errors
from pydantic import BaseModel

from .db import spojeni
from .prihlasovani import Prihlaseny, prihlaseny

router = APIRouter(prefix="/api")


# --- schémata -------------------------------------------------------------------------------


class Slunce(BaseModel):
    """Začátek a konec občanského soumraku a východ a západ slunce (UTC); pro časovou osu
    desktopu i začátek ráno a konec večer nautického (12°) a astronomického (18°) soumraku –
    prázdné, když Slunce tak hluboko nesestoupí (v létě astronomický, docs/modul-desktop.md)."""

    tb: datetime | None
    sr: datetime | None
    ss: datetime | None
    te: datetime | None
    nr: datetime | None
    nv: datetime | None
    ar: datetime | None
    av: datetime | None


class Letiste(BaseModel):
    id: int
    kod: str
    nazev: str
    domovske: bool


class Den(BaseModel):
    den: date
    ted: datetime
    """Čas serveru – obrazovka podle něj počítá stopky (hodiny telefonu se mohou lišit)."""
    letiste: Letiste | None
    """Moje letiště na dnešek (můj provoz, jinak domovské) – sluneční časy, výchozí místa;
    místo se na páscích uvádí, jen když je jiné."""
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
    druh_provozu: str
    """PLACHTARSKY (kluzák a vlečný let) | MOTOROVY – souhrny dne (db/035)."""
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
    """Jen když není moje letiště."""
    misto_pristani: str | None
    """Jen když není moje letiště."""
    cas_vzletu: datetime | None
    cas_pristani: datetime | None
    doba_uctovana_min: int | None
    pocet_pristani: int | None
    pob: int
    """Počet osob na palubě (u výcviku, sóla a přezkoušení spočítaný z posádky)."""
    uloha: str | None
    """Popis úlohy „IU/8P Přezkoušení…“ (v_let, db/040)."""
    uloha_oznaceni: str | None
    """Označení úlohy „IU/8P“ – štítek na pásku."""
    prezkouseni: str | None
    """Typ přezkoušení „PC-SEP Přezkoušení…“ (u přezkoušení místo úlohy, db/041)."""
    prezkouseni_kod: str | None
    """Označení typu přezkoušení „PC-SEP“ – štítek na pásku."""
    pocet_tg: int
    posadka: list[Clen]
    duvod_zruseni: str | None
    zruseno: datetime | None
    dodatecne: bool
    zalozeno: datetime
    varovani: str | None
    """Proč je pásek červený (po konci soumraku, přes maximální dobu letu)."""


class RadekSouhrnu(BaseModel):
    """Souhrn dne po druhu provozu a letadle (v_souhrn_dne, db/036) – ukončené lety."""

    druh_provozu: str
    rejstrik: str
    je_vlecny: bool
    lety: int
    pristani: int
    minut: int


class LetyDne(BaseModel):
    ted: datetime
    lety: list[Pasek]
    souhrn: list[RadekSouhrnu]


# --- pomocné --------------------------------------------------------------------------------


def _den_a_letiste(
    conn: Connection, den: date | None, relace_id: str
) -> tuple[date, datetime, dict | None]:
    """Den (dnes v UTC, není-li zadán), čas serveru a moje letiště na dnešek (db/026)."""
    r = conn.execute(
        """SELECT (now() AT TIME ZONE 'UTC')::date AS dnes, now() AS ted,
                  (SELECT json_build_object('id', letiste_id, 'kod', kod, 'nazev', nazev,
                                            'domovske', domovske,
                                            'sirka', zem_sirka, 'delka', zem_delka)
                   FROM lkkl.v_relace_letiste WHERE relace_id = %s) AS letiste""",
        (relace_id,),
    ).fetchone()
    return den or r["dnes"], r["ted"], r["letiste"]


def moje_letiste_id(conn: Connection, relace_id: str) -> int | None:
    """Letiště relace na dnešek – výchozí místo vzletu a přistání."""
    r = conn.execute(
        "SELECT letiste_id FROM lkkl.v_relace_letiste WHERE relace_id = %s", (relace_id,)
    ).fetchone()
    return r["letiste_id"] if r else None


def _soumrak(funkce, misto: Observer, den: date, stupnu: int) -> datetime | None:
    """Začátek (dawn) nebo konec (dusk) soumraku; None, když Slunce tak hluboko nesestoupí."""
    try:
        return funkce(misto, den, depression=stupnu, tzinfo=UTC)
    except ValueError:
        return None


def slunce(letiste: dict | None, den: date) -> Slunce:
    """Sluneční časy pro souřadnice letiště (knihovna astral, občanský soumrak 6°)."""
    if not letiste or letiste["sirka"] is None or letiste["delka"] is None:
        return Slunce(tb=None, sr=None, ss=None, te=None, nr=None, nv=None, ar=None, av=None)
    misto = Observer(float(letiste["sirka"]), float(letiste["delka"]))
    s = sun(misto, den, tzinfo=UTC)
    return Slunce(
        tb=s["dawn"],
        sr=s["sunrise"],
        ss=s["sunset"],
        te=s["dusk"],
        nr=_soumrak(dawn, misto, den, 12),
        nv=_soumrak(dusk, misto, den, 12),
        ar=_soumrak(dawn, misto, den, 18),
        av=_soumrak(dusk, misto, den, 18),
    )


def doba(minut: int) -> str:
    """Doba letu zápisem 1°02" (hodiny a minuty), pod hodinu 45"."""
    return f'{minut // 60}°{minut % 60:02d}"' if minut >= 60 else f'{minut}"'


def varovani(let: dict, ted: datetime, te: datetime | None) -> str | None:
    if let["stav"] != "VE_VZDUCHU":
        return None
    duvody = []
    if te and ted > te:
        duvody.append(f"Po konci občanského soumraku (TE {te:%H:%M})")
    if let["prekrocena_doba"]:  # v_let (db/036)
        duvody.append(f"Přes maximální dobu letu ({doba(let['max_doba_min'])})")
    return " · ".join(duvody) or None


# --- adresy ---------------------------------------------------------------------------------


@router.get("/den", response_model=Den)
def den_info(
    den: date | None = None,
    p: Prihlaseny = Depends(prihlaseny),
    conn: Connection = Depends(spojeni),
):
    """Den do hlavičky: datum, čas serveru, moje letiště a jeho sluneční časy."""
    den, ted, letiste = _den_a_letiste(conn, den, p.relace_id)
    return Den(den=den, ted=ted, letiste=letiste, slunce=slunce(letiste, den))


@router.get("/lety", response_model=LetyDne)
def lety(
    den: date | None = None,
    p: Prihlaseny = Depends(prihlaseny),
    conn: Connection = Depends(spojeni),
):
    """Lety dne pro pásky; dnes i všechno, co je ve vzduchu (i kdyby vzlétlo včera)."""
    den, ted, letiste = _den_a_letiste(conn, den, p.relace_id)
    moje_kod = letiste["kod"] if letiste else None
    radky = conn.execute(
        """SELECT v.id, v.stav, v.rejstrik, v.typ, v.kategorie_kod, v.druh_provozu,
                  v.ucel, v.ucel_kod, v.zpusob_vzletu, v.zpusob_vzletu_kod, v.je_vlecny,
                  v.vlecny_let_id,
                  v.vleceny_let_id, coalesce(av.rejstrik, ak.rejstrik) AS vlek_rejstrik,
                  nullif(v.misto_vzletu, %(moje)s) AS misto_vzletu,
                  nullif(v.misto_pristani, %(moje)s) AS misto_pristani,
                  v.cas_vzletu, v.cas_pristani, v.doba_uctovana_min, v.pocet_pristani,
                  v.pob, v.uloha, v.uloha_oznaceni, v.prezkouseni, v.prezkouseni_kod,
                  a.max_doba_min, v.prekrocena_doba,
                  v.duvod_zruseni,
                  v.zruseno, v.dodatecne,
                  v.zalozeno,
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
        {"den": den, "moje": moje_kod},
    ).fetchall()
    te = slunce(letiste, den).te
    souhrn = conn.execute(
        """SELECT druh_provozu, rejstrik, je_vlecny, lety, pristani, minut
           FROM lkkl.v_souhrn_dne WHERE den = %s ORDER BY rejstrik, je_vlecny""",
        (den,),
    ).fetchall()
    return LetyDne(
        ted=ted, lety=[Pasek(**r, varovani=varovani(r, ted, te)) for r in radky], souhrn=souhrn
    )


# --- akce letu: vzlet, přistání, T&G, zpět ---------------------------------------------------

PREKRYV = "Letadlo v tu dobu už letí – překrývá se s jiným letem."


@contextmanager
def zmena(conn: Connection) -> Iterator[None]:
    """Změna letu v jedné transakci; pravidla databáze (kontroly letu odložené na konec
    transakce) se vyhodnotí po všech příkazech změny a jejich chyba se vrátí jako
    srozumitelná hláška."""
    try:
        with conn.transaction():
            # Kontroly letu až po celé změně (např. výměna PIC = odebrat a přidat), i když
            # předchozí změna ve stejné transakci (testy) přepnula kontroly na okamžité.
            conn.execute("SET CONSTRAINTS ALL DEFERRED")
            yield
            conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
    except errors.RaiseException as e:
        zprava = re.sub(r"^Let \d+: ", "", e.diag.message_primary or "")
        raise HTTPException(400, zprava[:1].upper() + zprava[1:]) from e
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
    """Přistání teď; místo přistání zůstane, jak je u letu (plán), přistání celkem = T&G + 1."""
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
                   SET cas_pristani = NULL, pocet_pristani = NULL
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
                  a.poloha, a.poloha_letiste_id, a.poloha_popis,
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
           LEFT JOIN lkkl.v_lov_funkce f ON f.id = uf.funkce_id
           GROUP BY u.id, u.kod, u.nazev, u.poradi, lu.uloha_povinna
           ORDER BY u.poradi, u.nazev"""
    ).fetchall()
    return {
        "letadla": letadla,
        "ucely": ucely,
        "pic_id": conn.execute("SELECT id FROM lkkl.lov_funkce WHERE kod = 'PIC'").fetchone()["id"],
        "zpusoby": conn.execute("SELECT id, kod, nazev FROM lkkl.v_lov_zpusob_vzletu").fetchall(),
        "duvody_zruseni": conn.execute(
            "SELECT id, kod, nazev FROM lkkl.v_lov_duvod_zruseni"
        ).fetchall(),
        "letiste": conn.execute(
            # rychlá volba = nabízí se hned, ostatní přes Hledat… (db/028)
            "SELECT id, kod, nazev, domovske, rychla_volba FROM lkkl.v_lov_letiste"
        ).fetchall(),
        # u osoby role, které smí zastat podle oprávnění (účel – prázdný = vlečný let, funkce,
        # kategorie letadla), a typy přezkoušení, které smí provést (examinátor, db/041);
        # průvodce podle nich nabízí osoby do posádky
        "osoby": conn.execute(
            """SELECT o.id, o.jmeno, o.prijmeni,
                      coalesce((SELECT json_agg(json_build_object('ucel', s.ucel_kod,
                                                                  'funkce', s.funkce_kod,
                                                                  'kategorie', s.kategorie_kod))
                                FROM lkkl.v_osoba_smi s WHERE s.osoba_id = o.id), '[]') AS role,
                      coalesce((SELECT array_agg(s.prezkouseni_id)
                                FROM lkkl.v_osoba_prezkouseni s WHERE s.osoba_id = o.id),
                               '{}'::bigint[]) AS prezkouseni
               FROM lkkl.lov_osoba o
               WHERE o.platny
               ORDER BY o.prijmeni, o.jmeno"""
        ).fetchall(),
        "prezkouseni": conn.execute(
            """SELECT p.id, p.kod, p.nazev, p.popis, k.kod AS kategorie_kod
               FROM lkkl.v_lov_prezkouseni p
               JOIN lkkl.lov_kategorie k ON k.id = p.kategorie_id
               ORDER BY p.poradi, p.nazev"""
        ).fetchall(),
        "ulohy": conn.execute(
            """SELECT u.id, u.oznaceni, u.nazev, u.popis, u.osnova_id, u.osnova_popis AS osnova,
                      u.ucel_id, k.kod AS kategorie_kod
               FROM lkkl.v_uloha_nabidka u
               LEFT JOIN lkkl.lov_kategorie k ON k.id = u.kategorie_id
               -- pořadí osnov a úloh podle číselníku (spojení pořadí z pohledu nezaručí)
               ORDER BY u.osnova_poradi, u.osnova, u.poradi, u.nazev"""
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
    prezkouseni_id: int | None = None
    """Typ přezkoušení (jen u účelu Přezkoušení)."""
    platce_id: int | None = None
    """Prázdné a ne aeroklub = podle posádky (žák / přezkoušený, jinak PIC)."""
    plati_aeroklub: bool = False
    akce: Literal["vzlet", "naplanovat", "probehly"]
    cas_vzletu: datetime | None = None
    cas_pristani: datetime | None = None
    pocet_pristani: int = 1
    cas_pristani_vlecne: datetime | None = None
    """Proběhlý aerovlek: kdy přistála vlečná."""
    misto_vzletu_id: int | None = None
    misto_vzletu_popis: str | None = None
    """Místo vzletu (letiště, nebo popis); nezadané = moje letiště."""
    misto_pristani_id: int | None = None
    misto_pristani_popis: str | None = None
    """Místo přistání – do přistání plán (cíl); nezadané = moje letiště. U aerovleku pro
    kluzák i vlečnou (spolu se vrací, nebo spolu přeletí)."""


def _zalozit(conn: Connection, udaje: dict, posadka: list[ClenIn]) -> int:
    let_id = conn.execute(
        """INSERT INTO lkkl.let (letadlo_id, ucel_id, zpusob_vzletu_id, vlecny_let_id,
               cas_vzletu, cas_pristani, pocet_pristani, pob, platce_id, plati_aeroklub,
               uloha_id, prezkouseni_id, zalozil_id, misto_vzletu_id, misto_vzletu_popis,
               misto_pristani_id, misto_pristani_popis)
           VALUES (%(letadlo_id)s, %(ucel_id)s, %(zpusob_vzletu_id)s, %(vlecny_let_id)s,
                   CASE WHEN %(ted)s THEN now() ELSE %(cas_vzletu)s END, %(cas_pristani)s,
                   CASE WHEN %(cas_pristani)s::timestamptz IS NOT NULL
                        THEN %(pocet_pristani)s END,
                   %(pob)s, %(platce_id)s, %(plati_aeroklub)s, %(uloha_id)s,
                   %(prezkouseni_id)s, %(zalozil_id)s,
                   %(misto_vzletu_id)s::bigint, %(misto_vzletu_popis)s::text,
                   %(misto_pristani_id)s::bigint, %(misto_pristani_popis)s::text)
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
            "SELECT id FROM lkkl.v_lov_funkce WHERE na_palube AND kod <> 'PIC'"
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
    if probehly:
        casy = [data.cas_vzletu, data.cas_pristani]
        if data.vlecna_id is not None:
            casy.append(data.cas_pristani_vlecne)
        if any(c is None for c in casy):
            raise HTTPException(400, "Chybí čas vzletu nebo přistání.")
    pic_id = conn.execute("SELECT id FROM lkkl.lov_funkce WHERE kod = 'PIC'").fetchone()["id"]
    platce_id = data.platce_id
    if platce_id is None and not data.plati_aeroklub:
        platce_id = _vychozi_platce(conn, data.posadka, pic_id)

    # nezadané místo vzletu i přistání = moje letiště (výslovně, ne domovské z databáze)
    moje = moje_letiste_id(conn, p.relace_id)
    vzlet_popis = (data.misto_vzletu_popis or "").strip() or None
    pristani_popis = (data.misto_pristani_popis or "").strip() or None
    spolecne = {
        "ted": data.akce == "vzlet",
        "cas_vzletu": data.cas_vzletu if probehly else None,
        "platce_id": platce_id,
        "plati_aeroklub": data.plati_aeroklub,
        "zalozil_id": p.osoba_id,
        "misto_vzletu_id": data.misto_vzletu_id or (None if vzlet_popis else moje),
        "misto_vzletu_popis": vzlet_popis,
    }
    pristani = {
        "misto_pristani_id": data.misto_pristani_id or (None if pristani_popis else moje),
        "misto_pristani_popis": pristani_popis,
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
                    "prezkouseni_id": None,
                    **pristani,
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
                "prezkouseni_id": data.prezkouseni_id,
                **pristani,
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


# --- detail letu: údaje, historie, zrušení, obnovení, úpravy ---------------------------------


@router.get("/lety/{let_id}")
def detail(let_id: int, p: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)):
    """Všechny údaje letu, posádka, časy T&G a historie z auditu (docs/modul-lety.md 3.5)."""
    let = conn.execute(
        """SELECT v.id, v.verze, v.stav, v.letadlo_id, v.rejstrik, v.typ, v.kategorie,
                  v.kategorie_kod, t.pocet_mist, a.max_doba_min, v.prekrocena_doba,
                  v.ucel_id, v.ucel, v.ucel_kod, v.uloha_id, v.uloha, v.uloha_oznaceni,
                  v.prezkouseni_id, v.prezkouseni, v.prezkouseni_kod,
                  v.zpusob_vzletu, v.zpusob_vzletu_kod, v.je_vlecny,
                  l.misto_vzletu_id, l.misto_vzletu_popis, v.misto_vzletu,
                  l.misto_pristani_id, l.misto_pristani_popis, v.misto_pristani,
                  v.cas_vzletu, v.cas_pristani, v.doba_min, v.doba_uctovana_min,
                  v.pocet_pristani, v.pob, l.pob AS pob_zadany,
                  v.platce_id, v.plati_aeroklub, v.platce_jmeno, v.platce_prijmeni, v.poznamka,
                  v.duvod_zruseni, v.zruseno, v.dodatecne, v.zalozeno,
                  zl.jmeno || ' ' || zl.prijmeni AS zalozil,
                  zr.jmeno || ' ' || zr.prijmeni AS zrusil,
                  coalesce(v.vlecny_let_id, v.vleceny_let_id) AS vlek_let_id
           FROM lkkl.v_let v
           JOIN lkkl.let l ON l.id = v.id
           JOIN lkkl.lov_letadlo a ON a.id = v.letadlo_id
           JOIN lkkl.lov_typ t ON t.id = a.typ_id
           JOIN lkkl.lov_osoba zl ON zl.id = v.zalozil_id
           LEFT JOIN lkkl.lov_osoba zr ON zr.id = l.zrusil_id
           WHERE v.id = %s""",
        (let_id,),
    ).fetchone()
    if let is None:
        raise HTTPException(404, "Let neexistuje.")
    let["posadka"] = conn.execute(
        """SELECT p.osoba_id, o.jmeno, o.prijmeni, p.funkce_id, f.kod AS funkce_kod,
                  f.nazev AS funkce
           FROM lkkl.posadka p
           JOIN lkkl.lov_osoba o ON o.id = p.osoba_id
           JOIN lkkl.lov_funkce f ON f.id = p.funkce_id
           WHERE p.let_id = %s ORDER BY f.poradi""",
        (let_id,),
    ).fetchall()
    let["tg"] = [
        r["cas"]
        for r in conn.execute(
            "SELECT cas FROM lkkl.let_tg WHERE let_id = %s ORDER BY cas", (let_id,)
        ).fetchall()
    ]
    let["vlek"] = (
        conn.execute(
            """SELECT v.id AS let_id, v.rejstrik, v.pic_jmeno || ' ' || v.pic_prijmeni AS pilot
               FROM lkkl.v_let v WHERE v.id = %s""",
            (let["vlek_let_id"],),
        ).fetchone()
        if let["vlek_let_id"]
        else None
    )
    let["historie"] = conn.execute(
        """SELECT kdy, kdo, akce, popis FROM lkkl.v_historie_letu
           WHERE let_id = %s ORDER BY kdy, transakce""",
        (let_id,),
    ).fetchall()
    den, ted, letiste = _den_a_letiste(conn, None, p.relace_id)
    let["varovani"] = varovani(let, ted, slunce(letiste, den).te)
    return let


class ZrusitIn(BaseModel):
    duvod_id: int


@router.post("/lety/{let_id}/zrusit", response_model=Provedeno)
def zrusit(
    let_id: int,
    data: ZrusitIn,
    p: Prihlaseny = Depends(prihlaseny),
    conn: Connection = Depends(spojeni),
):
    """Let se nemaže, jen zruší s důvodem. Naplánovaný vlek se ruší celý (oba lety dvojice);
    po vzletu je každý let samostatný (např. kluzák po přetrženém laně – vlečná letí dál)."""
    let = _let(conn, let_id)
    with zmena(conn):
        radky = conn.execute(
            f"""UPDATE lkkl.let
                SET zruseni_duvod_id = %(duvod)s, zruseno = now(), zrusil_id = %(kdo)s
                WHERE id IN ({DVOJICE}) AND zruseni_duvod_id IS NULL
                  AND (id = %(id)s OR cas_vzletu IS NULL)""",  # noqa: S608 – pevný text
            {"id": let_id, "duvod": data.duvod_id, "kdo": p.osoba_id},
        ).rowcount
    if not radky:
        raise HTTPException(409, f"{let['rejstrik']}: let už je zrušený.")
    return Provedeno(let_id=let_id, rejstrik=let["rejstrik"], akce="zrusit", cas=None)


@router.post("/lety/{let_id}/obnovit", response_model=Provedeno)
def obnovit(let_id: int, _: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)):
    let = _let(conn, let_id)
    with zmena(conn):
        radky = conn.execute(
            f"""UPDATE lkkl.let SET zruseni_duvod_id = NULL, zruseno = NULL, zrusil_id = NULL
                WHERE id IN ({DVOJICE}) AND zruseni_duvod_id IS NOT NULL""",  # noqa: S608
            {"id": let_id},
        ).rowcount
    if not radky:
        raise HTTPException(409, f"{let['rejstrik']}: let není zrušený.")
    return Provedeno(let_id=let_id, rejstrik=let["rejstrik"], akce="obnovit", cas=None)


class Uprava(BaseModel):
    """Úprava z detailu: číslo verze a jen změněné údaje (prázdná hodnota = smazat)."""

    verze: int
    letadlo_id: int | None = None
    pob: int | None = None
    uloha_id: int | None = None
    prezkouseni_id: int | None = None
    platce_id: int | None = None
    plati_aeroklub: bool | None = None
    poznamka: str | None = None
    cas_vzletu: datetime | None = None
    cas_pristani: datetime | None = None
    misto_vzletu_id: int | None = None
    misto_vzletu_popis: str | None = None
    misto_pristani_id: int | None = None
    misto_pristani_popis: str | None = None
    pocet_pristani: int | None = None
    posadka: list[ClenIn] | None = None


# Místo je letiště, nebo popis (přistání do terénu) – zadané jedno smaže druhé.
DRUHA_POLOVINA = {
    "misto_vzletu_id": "misto_vzletu_popis",
    "misto_vzletu_popis": "misto_vzletu_id",
    "misto_pristani_id": "misto_pristani_popis",
    "misto_pristani_popis": "misto_pristani_id",
}


@router.post("/lety/{let_id}")
def upravit(
    let_id: int,
    data: Uprava,
    p: Prihlaseny = Depends(prihlaseny),
    conn: Connection = Depends(spojeni),
):
    """Úprava údajů letu; změnil-li let mezitím někdo jiný (jiná verze), odmítne se."""
    let = _let(conn, let_id)
    zmeny = data.model_dump(exclude_unset=True, exclude={"verze", "posadka"})
    if isinstance(zmeny.get("poznamka"), str):
        zmeny["poznamka"] = zmeny["poznamka"].strip() or None
    for pole, druhe in DRUHA_POLOVINA.items():
        if zmeny.get(pole) is not None and druhe not in zmeny:
            zmeny[druhe] = None
    if zmeny.get("platce_id") is not None:
        zmeny["plati_aeroklub"] = False
    elif zmeny.get("plati_aeroklub"):
        zmeny["platce_id"] = None
    with zmena(conn):
        aktualni = conn.execute(
            "SELECT verze, zruseni_duvod_id FROM lkkl.let WHERE id = %s FOR UPDATE", (let_id,)
        ).fetchone()
        if aktualni["verze"] != data.verze:
            raise HTTPException(
                409, f"{let['rejstrik']}: let mezitím změnil někdo jiný – ukazuji aktuální stav."
            )
        if aktualni["zruseni_duvod_id"] is not None:
            raise HTTPException(409, "Zrušený let nejde upravit – nejdřív ho obnovte.")
        # Sloupce jen z pevného seznamu modelu Uprava; i bez změny letu se zvýší verze.
        nastavit = ", ".join(f"{s} = %({s})s" for s in zmeny) or "verze = verze"
        conn.execute(
            f"UPDATE lkkl.let SET {nastavit} WHERE id = %(id)s",  # noqa: S608
            {**zmeny, "id": let_id},
        )
        if "cas_vzletu" in zmeny:  # kluzák a vlečná vzlétají společně (db/035)
            conn.execute(
                f"""UPDATE lkkl.let SET cas_vzletu = %(cas)s
                    WHERE id IN ({DVOJICE}) AND id <> %(id)s""",  # noqa: S608 – pevný text
                {"cas": zmeny["cas_vzletu"], "id": let_id},
            )
        if data.posadka is not None:
            nove = {(c.osoba_id, c.funkce_id) for c in data.posadka}
            stare = {
                (r["osoba_id"], r["funkce_id"])
                for r in conn.execute(
                    "SELECT osoba_id, funkce_id FROM lkkl.posadka WHERE let_id = %s", (let_id,)
                ).fetchall()
            }
            for osoba_id, funkce_id in stare - nove:
                conn.execute(
                    """DELETE FROM lkkl.posadka
                       WHERE let_id = %s AND osoba_id = %s AND funkce_id = %s""",
                    (let_id, osoba_id, funkce_id),
                )
            for osoba_id, funkce_id in nove - stare:
                conn.execute(
                    "INSERT INTO lkkl.posadka (let_id, osoba_id, funkce_id) VALUES (%s, %s, %s)",
                    (let_id, osoba_id, funkce_id),
                )
    return detail(let_id, p, conn)
