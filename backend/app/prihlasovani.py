"""Účty a přihlašování (návrh: docs/modul-prihlasovani.md)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from psycopg import Connection, errors
from pydantic import BaseModel, create_model

from . import bezpecnost, db, posta
from .db import nastavit_kontext, spojeni
from .nastaveni import nastaveni

router = APIRouter(prefix="/api")

COOKIE = "lkkl_relace"
PLATNOST_RELACE = timedelta(days=30)
PRODLOUZIT_PO = timedelta(hours=1)
MAX_POKUSU = 5
BLOKACE = timedelta(minutes=15)

CHYBA_PRIHLASENI = "Nesprávný e-mail nebo heslo."
CHYBA_ODKAZU = "Odkaz neplatí nebo vypršel. Požádejte admina o nový."


# --- schémata -------------------------------------------------------------------------------


class Prava(BaseModel):
    """Práva účtu – jediný seznam v kódu (sloupce `lkkl.ucet`, vstupy i výstupy rozhraní;
    docs/modul-osoby.md). Admin smí vše; `Ja.prava` to už má započtené."""

    admin: bool = False
    smi_odblokovat: bool = False
    spravuje_osoby: bool = False
    spravuje_letadla: bool = False
    spravuje_vycvik: bool = False


PRAVA = tuple(Prava.model_fields)
SLOUPCE_PRAV = ", ".join(PRAVA)  # do SQL jen pevné názvy z modelu (noqa S608 níže)


class OsobaKratce(BaseModel):
    osoba_id: int
    jmeno: str
    prijmeni: str


class OsobaSEmailem(OsobaKratce):
    email: str


class Ja(OsobaSEmailem):
    prava: Prava
    puvodni: OsobaKratce | None
    """Skutečný admin, pokud je přihlášen jako jiná osoba."""
    jen_cteni: bool
    """Relace jen ke čtení (sdílený počítač): zápisy server odmítne, práva vypnutá."""


class PrihlaseniIn(BaseModel):
    email: str
    heslo: str
    jen_cteni: bool = False
    """Sdílený počítač (klubovna): relace jen ke čtení (docs/modul-desktop.md 6.1)."""


class Zarizeni(BaseModel):
    zarizeni: str | None
    vytvorena: datetime
    posledni_aktivita: datetime
    aktualni: bool


class NastavitHesloIn(BaseModel):
    klic: str
    heslo: str


class ZmenitHesloIn(BaseModel):
    stare: str
    nove: str


class UcetIn(Prava):
    osoba_id: int


# Změna účtu: přihlášení a každé právo zvlášť, jen poslané (None = beze změny).
UcetZmenaIn = create_model(
    "UcetZmenaIn",
    prihlaseni_povoleno=(bool | None, None),
    **{pravo: (bool | None, None) for pravo in PRAVA},
)


class Ucet(OsobaSEmailem, Prava):
    ma_heslo: bool
    smi_se_prihlasit: bool
    zalozen: datetime
    pozvanka_odeslana: datetime | None
    posledni_prihlaseni: datetime | None
    zablokovano: bool


class Zablokovany(OsobaKratce):
    zablokovano_do: datetime


class Odkaz(BaseModel):
    odkaz: str


class OdeslanyEmail(BaseModel):
    adresa: str
    kdy: datetime


# --- relace a oprávnění ---------------------------------------------------------------------


@dataclass(frozen=True)
class Prihlaseny:
    relace_id: str
    osoba_id: int
    puvodni_osoba_id: int | None
    prava: Prava
    """Práva z účtu (bez „admin smí vše“); v relaci jen ke čtení všechna vypnutá."""
    jen_cteni: bool

    @property
    def admin(self) -> bool:
        return self.prava.admin

    def smi(self, pravo: str) -> bool:
        """Má právo, nebo je admin."""
        return self.prava.admin or getattr(self.prava, pravo)


JEN_CTENI = "Přihlášeno jen ke čtení – pro změny se odhlaste a přihlaste znovu."


def _nastavit_cookie(response: Response, klic: str) -> None:
    response.set_cookie(
        COOKIE,
        klic,
        max_age=int(PLATNOST_RELACE.total_seconds()),
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def _smazat_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE, httponly=True, secure=True, samesite="lax", path="/")


def smazat_relace(conn: Connection, podminka: str, parametry: tuple) -> int:
    """Smaže relace podle podmínky (pevný text v kódu) i s jejich nastavením „můj provoz“
    (db/026; cizí klíče jsou bez kaskádového mazání)."""
    relace = f"SELECT id FROM lkkl.relace WHERE {podminka}"  # noqa: S608 – pevný text
    with conn.transaction():
        for tabulka in ("relace_provoz_osoba", "relace_provoz"):
            conn.execute(
                f"DELETE FROM lkkl.{tabulka} WHERE relace_id IN ({relace})",  # noqa: S608
                parametry,
            )
        return conn.execute(
            f"DELETE FROM lkkl.relace WHERE {podminka}",  # noqa: S608 – pevný text
            parametry,
        ).rowcount


def smazat_prosle_relace(conn: Connection, osoba_id: int | None = None) -> int:
    """Úklid prošlých relací (všech, nebo jedné osoby) – aplikace ho dělá sama při startu
    a při přihlášení, žádný cron není potřeba."""
    if osoba_id is None:
        return smazat_relace(conn, "plati_do <= now()", ())
    return smazat_relace(conn, "plati_do <= now() AND osoba_id = %s", (osoba_id,))


def _nova_relace(conn: Connection, osoba_id: int, request: Request, jen_cteni: bool = False) -> str:
    smazat_prosle_relace(conn, osoba_id)
    klic, otisk = bezpecnost.novy_klic_relace()
    zarizeni = request.headers.get("user-agent", "")[:200] or None
    conn.execute(
        """INSERT INTO lkkl.relace (id, osoba_id, plati_do, zarizeni, jen_cteni)
           VALUES (%s, %s, now() + %s, %s, %s)""",
        (otisk, osoba_id, PLATNOST_RELACE, zarizeni, jen_cteni),
    )
    return klic


def prihlaseny(
    request: Request, response: Response, conn: Connection = Depends(spojeni)
) -> Prihlaseny:
    """Závislost: platná relace z cookie, jinak 401. Relaci průběžně prodlužuje.
    Relace jen ke čtení smí jen číst – každý jiný požadavek odmítne (403) a práva vypne;
    všechny zápisy aplikace jdou přes tuto závislost (test test_jen_cteni_zadny_zapis)."""
    klic = request.cookies.get(COOKIE)
    if not klic:
        raise HTTPException(401, "Nejste přihlášen.")
    otisk = bezpecnost.otisk_klice(klic)
    prava_uctu = ", ".join(f"u.{pravo}" for pravo in PRAVA)
    r = conn.execute(
        f"""SELECT r.osoba_id, r.puvodni_osoba_id, r.jen_cteni, {prava_uctu},
                  r.posledni_aktivita < now() - %s AS prodlouzit
           FROM lkkl.relace r
           JOIN lkkl.v_ucet u ON u.osoba_id = r.osoba_id
           LEFT JOIN lkkl.v_ucet p ON p.osoba_id = r.puvodni_osoba_id
           WHERE r.id = %s
             AND r.plati_do > now()
             AND u.smi_se_prihlasit
             AND (r.puvodni_osoba_id IS NULL OR (p.smi_se_prihlasit AND p.admin))""",  # noqa: S608
        (PRODLOUZIT_PO, otisk),
    ).fetchone()
    if r is None:
        smazat_relace(conn, "id = %s", (otisk,))
        smazat = Response()
        _smazat_cookie(smazat)
        raise HTTPException(
            401, "Přihlášení vypršelo.", headers={"set-cookie": smazat.headers["set-cookie"]}
        )
    if r["prodlouzit"]:
        conn.execute(
            """UPDATE lkkl.relace SET posledni_aktivita = now(), plati_do = now() + %s
               WHERE id = %s""",
            (PLATNOST_RELACE, otisk),
        )
        _nastavit_cookie(response, klic)
    jen_cteni = r["jen_cteni"]
    if jen_cteni and request.method not in ("GET", "HEAD"):
        raise HTTPException(403, JEN_CTENI)
    nastavit_kontext(conn, r["osoba_id"], r["puvodni_osoba_id"])  # pro audit
    return Prihlaseny(
        relace_id=otisk,
        osoba_id=r["osoba_id"],
        puvodni_osoba_id=r["puvodni_osoba_id"],
        prava=Prava(**{pravo: r[pravo] and not jen_cteni for pravo in PRAVA}),
        jen_cteni=jen_cteni,
    )


def pravo(nazev: str):
    """Závislost: přihlášený s daným právem (nebo admin), jinak 403."""

    def zavislost(p: Prihlaseny = Depends(prihlaseny)) -> Prihlaseny:
        if not p.smi(nazev):
            raise HTTPException(403, "Na tuto akci nemáte právo.")
        return p

    zavislost.__name__ = nazev
    return zavislost


admin = pravo("admin")
smi_odblokovat = pravo("smi_odblokovat")
spravuje_osoby = pravo("spravuje_osoby")
spravuje_letadla = pravo("spravuje_letadla")
spravuje_vycvik = pravo("spravuje_vycvik")


def _ja(
    conn: Connection, osoba_id: int, puvodni_osoba_id: int | None, jen_cteni: bool = False
) -> Ja:
    u = conn.execute(
        f"""SELECT osoba_id, jmeno, prijmeni, email, {SLOUPCE_PRAV}
            FROM lkkl.v_ucet WHERE osoba_id = %s""",  # noqa: S608 – pevné názvy sloupců
        (osoba_id,),
    ).fetchone()
    puvodni = None
    if puvodni_osoba_id is not None:
        puvodni = conn.execute(
            "SELECT osoba_id, jmeno, prijmeni FROM lkkl.v_ucet WHERE osoba_id = %s",
            (puvodni_osoba_id,),
        ).fetchone()
    return Ja(
        osoba_id=u["osoba_id"],
        jmeno=u["jmeno"],
        prijmeni=u["prijmeni"],
        email=u["email"],
        # admin má všechna práva; v relaci jen ke čtení žádná
        prava=Prava(**{pravo: (u["admin"] or u[pravo]) and not jen_cteni for pravo in PRAVA}),
        puvodni=OsobaKratce(**puvodni) if puvodni else None,
        jen_cteni=jen_cteni,
    )


# --- přihlášení a odhlášení -----------------------------------------------------------------


@router.post("/prihlaseni", response_model=Ja)
def prihlaseni(
    data: PrihlaseniIn, request: Request, response: Response, conn: Connection = Depends(spojeni)
):
    vysledek, minut, osoba_id, klic = "chyba", 0, None, None
    # Počítadlo pokusů se musí uložit i při neúspěchu – chyba se proto hlásí až po transakci.
    with conn.transaction():
        u = conn.execute(
            """SELECT u.osoba_id, u.heslo_hash, u.neuspesne_pokusy,
                      u.prihlaseni_povoleno AND o.platny AS smi,
                      coalesce(u.zablokovano_do > now(), false) AS zablokovano,
                      ceil(extract(epoch FROM u.zablokovano_do - now()) / 60)::int AS minut
               FROM lkkl.ucet u
               JOIN lkkl.lov_osoba o ON o.id = u.osoba_id
               WHERE lower(o.email) = lower(%s)
               FOR UPDATE OF u""",
            (data.email.strip(),),
        ).fetchone()
        if u is None or not u["smi"] or u["heslo_hash"] is None:
            bezpecnost.over_heslo(None, data.heslo)  # stejně dlouhá odpověď
        elif u["zablokovano"]:
            vysledek, minut = "blokace", u["minut"]
        elif not bezpecnost.over_heslo(u["heslo_hash"], data.heslo):
            if u["neuspesne_pokusy"] + 1 >= MAX_POKUSU:
                conn.execute(
                    """UPDATE lkkl.ucet SET neuspesne_pokusy = 0, zablokovano_do = now() + %s
                       WHERE osoba_id = %s""",
                    (BLOKACE, u["osoba_id"]),
                )
                vysledek, minut = "blokace", int(BLOKACE.total_seconds() // 60)
            else:
                conn.execute(
                    """UPDATE lkkl.ucet SET neuspesne_pokusy = neuspesne_pokusy + 1
                       WHERE osoba_id = %s""",
                    (u["osoba_id"],),
                )
        else:
            vysledek, osoba_id = "ok", u["osoba_id"]
            if bezpecnost.potrebuje_novy_otisk(u["heslo_hash"]):
                conn.execute(
                    "UPDATE lkkl.ucet SET heslo_hash = %s WHERE osoba_id = %s",
                    (bezpecnost.otisk_hesla(data.heslo), osoba_id),
                )
            conn.execute(
                """UPDATE lkkl.ucet
                   SET neuspesne_pokusy = 0, posledni_prihlaseni = now()
                   WHERE osoba_id = %s""",
                (osoba_id,),
            )
            klic = _nova_relace(conn, osoba_id, request, data.jen_cteni)
    if vysledek == "blokace":
        raise HTTPException(
            429,
            f"Příliš mnoho neúspěšných pokusů. Zkuste to za {minut} min, "
            "nebo požádejte o odblokování.",
        )
    if vysledek != "ok":
        raise HTTPException(401, CHYBA_PRIHLASENI)
    _nastavit_cookie(response, klic)
    return _ja(conn, osoba_id, None, data.jen_cteni)


@router.post("/odhlaseni", status_code=204)
def odhlaseni(request: Request, conn: Connection = Depends(spojeni)):
    klic = request.cookies.get(COOKIE)
    if klic:
        smazat_relace(conn, "id = %s", (bezpecnost.otisk_klice(klic),))
    odpoved = Response(status_code=204)
    _smazat_cookie(odpoved)
    return odpoved


@router.get("/ja", response_model=Ja)
def ja(p: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)):
    return _ja(conn, p.osoba_id, p.puvodni_osoba_id, p.jen_cteni)


@router.get("/zarizeni", response_model=list[Zarizeni])
def zarizeni(p: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)):
    return conn.execute(
        """SELECT zarizeni, vytvorena, posledni_aktivita, id = %s AS aktualni
           FROM lkkl.relace
           WHERE osoba_id = %s AND plati_do > now()
             AND (puvodni_osoba_id IS NULL OR id = %s)
           ORDER BY posledni_aktivita DESC""",
        (p.relace_id, p.osoba_id, p.relace_id),
    ).fetchall()


@router.post("/zarizeni/odhlasit-ostatni", status_code=204)
def odhlasit_ostatni(p: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)):
    smazat_relace(
        conn,
        "osoba_id = %s AND id <> %s AND puvodni_osoba_id IS NULL",
        (p.osoba_id, p.relace_id),
    )


# --- heslo ----------------------------------------------------------------------------------


def _osoba_z_platneho_odkazu(conn: Connection, klic: str) -> dict | None:
    """Účet z platného odkazu (řádek účtu zamčený do konce transakce), jinak None."""
    osoba_id = bezpecnost.osoba_z_odkazu(klic)
    if osoba_id is None:
        return None
    u = conn.execute(
        """SELECT u.osoba_id, u.heslo_zmeneno, v.jmeno, v.prijmeni, v.email, v.smi_se_prihlasit
           FROM lkkl.ucet u JOIN lkkl.v_ucet v ON v.osoba_id = u.osoba_id
           WHERE u.osoba_id = %s
           FOR UPDATE OF u""",
        (osoba_id,),
    ).fetchone()
    if (
        u is None
        or not u["smi_se_prihlasit"]
        or not bezpecnost.odkaz_plati(nastaveni.tajny_klic, klic, u["heslo_zmeneno"])
    ):
        return None
    return u


def _ulozit_heslo(conn: Connection, osoba_id: int, heslo: str) -> None:
    """Nové heslo zneplatní dřívější odkazy (heslo_zmeneno), vynuluje pokusy a zruší
    platné zablokování (prošlé nechá být, aby v auditu nevzniklo falešné odblokování)."""
    conn.execute(
        """UPDATE lkkl.ucet
           SET heslo_hash = %s, heslo_zmeneno = clock_timestamp(), neuspesne_pokusy = 0,
               zablokovano_do = CASE WHEN zablokovano_do > now() THEN NULL ELSE zablokovano_do END
           WHERE osoba_id = %s""",
        (bezpecnost.otisk_hesla(heslo), osoba_id),
    )


def _zkontrolovat_delku(heslo: str) -> None:
    if not bezpecnost.heslo_ma_spravnou_delku(heslo):
        od, do = bezpecnost.DELKA_HESLA
        raise HTTPException(400, f"Heslo musí mít {od} až {do} znaků.")


@router.get("/heslo/odkaz", response_model=OsobaSEmailem)
def heslo_odkaz(klic: str, conn: Connection = Depends(spojeni)):
    u = _osoba_z_platneho_odkazu(conn, klic)
    if u is None:
        raise HTTPException(400, CHYBA_ODKAZU)
    return u


@router.post("/heslo/nastavit", response_model=Ja)
def heslo_nastavit(
    data: NastavitHesloIn,
    request: Request,
    response: Response,
    conn: Connection = Depends(spojeni),
):
    _zkontrolovat_delku(data.heslo)
    with conn.transaction():
        u = _osoba_z_platneho_odkazu(conn, data.klic)
        if u is not None:
            osoba_id = u["osoba_id"]
            nastavit_kontext(conn, osoba_id)  # heslo si nastavuje sama osoba (pro audit)
            _ulozit_heslo(conn, osoba_id, data.heslo)
            smazat_relace(conn, "osoba_id = %s OR puvodni_osoba_id = %s", (osoba_id, osoba_id))
            conn.execute(
                "UPDATE lkkl.ucet SET posledni_prihlaseni = now() WHERE osoba_id = %s",
                (osoba_id,),
            )
            klic = _nova_relace(conn, osoba_id, request)
    if u is None:
        raise HTTPException(400, CHYBA_ODKAZU)
    _nastavit_cookie(response, klic)
    return _ja(conn, osoba_id, None)


@router.post("/heslo/zmenit", status_code=204)
def heslo_zmenit(
    data: ZmenitHesloIn, p: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)
):
    if p.puvodni_osoba_id is not None:
        raise HTTPException(403, "Při přihlášení za jinou osobu nejde měnit heslo.")
    _zkontrolovat_delku(data.nove)
    with conn.transaction():
        otisk = conn.execute(
            "SELECT heslo_hash FROM lkkl.ucet WHERE osoba_id = %s FOR UPDATE", (p.osoba_id,)
        ).fetchone()["heslo_hash"]
        spravne = bezpecnost.over_heslo(otisk, data.stare)
        if spravne:
            _ulozit_heslo(conn, p.osoba_id, data.nove)
            smazat_relace(
                conn,
                "(osoba_id = %s OR puvodni_osoba_id = %s) AND id <> %s",
                (p.osoba_id, p.osoba_id, p.relace_id),
            )
    if not spravne:
        raise HTTPException(400, "Současné heslo nesouhlasí.")


# --- účty (admin) ---------------------------------------------------------------------------

_UCET_SQL = f"""SELECT osoba_id, jmeno, prijmeni, email, ma_heslo, smi_se_prihlasit, {SLOUPCE_PRAV},
                      zalozen, pozvanka_odeslana, posledni_prihlaseni,
                      coalesce(zablokovano_do > now(), false) AS zablokovano
               FROM lkkl.v_ucet"""  # noqa: S608 – pevné názvy sloupců


def _jen_admin_prava(p: Prihlaseny, prava: dict) -> None:
    """Práva přiděluje (i odebírá) jen admin: poslané právo od správce osob = 403."""
    if not p.admin and prava:
        raise HTTPException(403, "Práva přiděluje jen admin.")


def jen_admin_na_admina(conn: Connection, p: Prihlaseny, osoba_id: int) -> None:
    """Do účtu admina (vypnutí, práva, odkaz pro heslo, e-mail osoby) smí jen admin – jinak by
    správce osob účet admina převzal (odkaz pro heslo, nebo změna e-mailu a pak odkaz)."""
    cil = conn.execute("SELECT admin FROM lkkl.ucet WHERE osoba_id = %s", (osoba_id,)).fetchone()
    if cil is not None and cil["admin"] and not p.admin:
        raise HTTPException(403, "Účet admina smí měnit jen admin.")


@router.get("/ucty", response_model=list[Ucet])
def ucty(_: Prihlaseny = Depends(spravuje_osoby), conn: Connection = Depends(spojeni)):
    return conn.execute(_UCET_SQL + " ORDER BY prijmeni, jmeno").fetchall()


@router.post("/ucty", response_model=Ucet)
def ucet_zalozit(
    data: UcetIn, p: Prihlaseny = Depends(spravuje_osoby), conn: Connection = Depends(spojeni)
):
    prava = data.model_dump(exclude={"osoba_id"})
    _jen_admin_prava(p, {k: v for k, v in prava.items() if v})
    hlasky = {
        errors.ForeignKeyViolation: "Osoba neexistuje.",
        errors.UniqueViolation: "Osoba už účet má.",
    }
    with db.transakce(conn, hlasky):
        conn.execute(
            f"""INSERT INTO lkkl.ucet (osoba_id, {SLOUPCE_PRAV})
                VALUES (%(osoba_id)s, {", ".join(f"%({pravo})s" for pravo in PRAVA)})""",  # noqa: S608
            data.model_dump(),
        )
    return conn.execute(_UCET_SQL + " WHERE osoba_id = %s", (data.osoba_id,)).fetchone()


@router.post("/ucty/{osoba_id}", response_model=Ucet)
def ucet_zmenit(
    osoba_id: int,
    data: UcetZmenaIn,  # type: ignore[valid-type]
    p: Prihlaseny = Depends(spravuje_osoby),
    conn: Connection = Depends(spojeni),
):
    zmeny = data.model_dump(exclude_unset=True, exclude_none=True)
    _jen_admin_prava(p, {k: v for k, v in zmeny.items() if k in PRAVA})  # i odebrání práva
    if osoba_id == p.osoba_id and (
        zmeny.get("prihlaseni_povoleno") is False or zmeny.get("admin") is False
    ):
        raise HTTPException(400, "Sám sobě nemůžete zablokovat účet ani odebrat admina.")
    jen_admin_na_admina(conn, p, osoba_id)
    with conn.transaction():
        nastavit = ", ".join(f"{k} = %({k})s" for k in zmeny) or "osoba_id = osoba_id"
        zmeneno = conn.execute(
            f"UPDATE lkkl.ucet SET {nastavit} WHERE osoba_id = %(osoba_id)s RETURNING osoba_id",  # noqa: S608
            {**zmeny, "osoba_id": osoba_id},
        ).fetchone()
        if zmeneno and zmeny.get("prihlaseni_povoleno") is False:
            smazat_relace(conn, "osoba_id = %s OR puvodni_osoba_id = %s", (osoba_id, osoba_id))
    if zmeneno is None:
        raise HTTPException(404, "Účet neexistuje.")
    return conn.execute(_UCET_SQL + " WHERE osoba_id = %s", (osoba_id,)).fetchone()


@router.post("/ucty/{osoba_id}/pozvanka", response_model=Odkaz)
def ucet_pozvanka(
    osoba_id: int, p: Prihlaseny = Depends(spravuje_osoby), conn: Connection = Depends(spojeni)
):
    jen_admin_na_admina(conn, p, osoba_id)
    u = conn.execute(
        """SELECT u.heslo_zmeneno, v.smi_se_prihlasit
           FROM lkkl.ucet u JOIN lkkl.v_ucet v ON v.osoba_id = u.osoba_id
           WHERE u.osoba_id = %s""",
        (osoba_id,),
    ).fetchone()
    if u is None:
        raise HTTPException(404, "Účet neexistuje.")
    if not u["smi_se_prihlasit"]:
        raise HTTPException(400, "Účet nebo osoba je zablokovaná.")
    conn.execute("UPDATE lkkl.ucet SET pozvanka_odeslana = now() WHERE osoba_id = %s", (osoba_id,))
    return Odkaz(odkaz=odkaz_pro_heslo(osoba_id, u["heslo_zmeneno"]))


PREDMET_ODKAZU = "AK Kladno Log – nastavení hesla"
TEXT_ODKAZU = """Dobrý den, {jmeno},

v aplikaci AK Kladno Log (evidence letů aeroklubu Kladno) máte připravený přístup.
Heslo si nastavíte tímto odkazem – platí 3 dny, po nastavení hesla už ne:
{odkaz}

Přihlašovací jméno je tato e-mailová adresa. Pokud jste o přístup nežádali, e-mail
ignorujte.{dotazy}

AK Kladno
"""


@router.post("/ucty/{osoba_id}/pozvanka-emailem", response_model=OdeslanyEmail)
def ucet_pozvanka_emailem(
    osoba_id: int, p: Prihlaseny = Depends(admin), conn: Connection = Depends(spojeni)
):
    """Odkaz pro nastavení hesla e-mailem z info@lkkl.cz – jen admin, ručně u jedné osoby
    (docs/modul-email.md); záznam v lkkl.email bez obsahu."""
    u = conn.execute(
        """SELECT u.heslo_zmeneno, v.smi_se_prihlasit, v.jmeno, v.email
           FROM lkkl.ucet u JOIN lkkl.v_ucet v ON v.osoba_id = u.osoba_id
           WHERE u.osoba_id = %s""",
        (osoba_id,),
    ).fetchone()
    if u is None:
        raise HTTPException(404, "Účet neexistuje.")
    if not u["smi_se_prihlasit"]:
        raise HTTPException(400, "Účet nebo osoba je zablokovaná.")
    if conn.execute(
        """SELECT 1 FROM lkkl.email WHERE osoba_id = %s AND chyba IS NULL
           AND kdy > now() - interval '5 minutes'""",
        (osoba_id,),
    ).fetchone():
        raise HTTPException(429, "Odkaz byl odeslán před chvílí – další jde poslat za 5 minut.")
    dotazy = (
        f" S dotazy se obraťte na {nastaveni.email_odpoved} (stačí odpovědět na tento e-mail)."
        if nastaveni.email_odpoved
        else ""
    )
    text = TEXT_ODKAZU.format(
        jmeno=u["jmeno"], odkaz=odkaz_pro_heslo(osoba_id, u["heslo_zmeneno"]), dotazy=dotazy
    )
    try:
        posta.odeslat(u["email"], PREDMET_ODKAZU, text)
        chyba = None
    except posta.ChybaPosty as e:
        chyba = str(e)
    zaznam = conn.execute(
        """INSERT INTO lkkl.email (druh, osoba_id, adresa, odeslal_id, chyba)
           VALUES ('ODKAZ_HESLO', %s, %s, %s, %s) RETURNING adresa, kdy""",
        (osoba_id, u["email"], p.osoba_id, chyba),
    ).fetchone()
    if chyba:
        raise HTTPException(502, f"E-mail se nepodařilo odeslat: {chyba}")
    conn.execute("UPDATE lkkl.ucet SET pozvanka_odeslana = now() WHERE osoba_id = %s", (osoba_id,))
    return zaznam


def odkaz_pro_heslo(osoba_id: int, heslo_zmeneno: datetime | None) -> str:
    klic = bezpecnost.podepsat_odkaz(nastaveni.tajny_klic, osoba_id, heslo_zmeneno)
    return f"{nastaveni.adresa}/heslo?klic={klic}"


@router.get("/ucty/zablokovane", response_model=list[Zablokovany])
def ucty_zablokovane(_: Prihlaseny = Depends(smi_odblokovat), conn: Connection = Depends(spojeni)):
    return conn.execute(
        """SELECT osoba_id, jmeno, prijmeni, zablokovano_do FROM lkkl.v_ucet
           WHERE zablokovano_do > now() ORDER BY prijmeni, jmeno"""
    ).fetchall()


@router.post("/ucty/{osoba_id}/odblokovat", status_code=204)
def ucet_odblokovat(
    osoba_id: int, _: Prihlaseny = Depends(smi_odblokovat), conn: Connection = Depends(spojeni)
):
    odblokovano = conn.execute(
        """UPDATE lkkl.ucet SET zablokovano_do = NULL, neuspesne_pokusy = 0
           WHERE osoba_id = %s RETURNING osoba_id""",
        (osoba_id,),
    ).fetchone()
    if odblokovano is None:
        raise HTTPException(404, "Účet neexistuje.")


# --- přihlásit se jako ----------------------------------------------------------------------


@router.post("/prihlasit-jako/konec", response_model=Ja)
def prihlasit_jako_konec(p: Prihlaseny = Depends(prihlaseny), conn: Connection = Depends(spojeni)):
    if p.puvodni_osoba_id is None:
        raise HTTPException(400, "Nejste přihlášen za jinou osobu.")
    conn.execute(
        "UPDATE lkkl.relace SET osoba_id = %s, puvodni_osoba_id = NULL WHERE id = %s",
        (p.puvodni_osoba_id, p.relace_id),
    )
    return _ja(conn, p.puvodni_osoba_id, None)


@router.post("/prihlasit-jako/{osoba_id}", response_model=Ja)
def prihlasit_jako(
    osoba_id: int, p: Prihlaseny = Depends(admin), conn: Connection = Depends(spojeni)
):
    cil = conn.execute(
        "SELECT smi_se_prihlasit, admin FROM lkkl.v_ucet WHERE osoba_id = %s", (osoba_id,)
    ).fetchone()
    if cil is None:
        raise HTTPException(404, "Účet neexistuje.")
    if osoba_id == p.osoba_id or cil["admin"]:
        raise HTTPException(400, "Za admina se přihlásit nejde.")
    if not cil["smi_se_prihlasit"]:
        raise HTTPException(400, "Účet nebo osoba je zablokovaná.")
    conn.execute(
        "UPDATE lkkl.relace SET osoba_id = %s, puvodni_osoba_id = %s WHERE id = %s",
        (osoba_id, p.osoba_id, p.relace_id),
    )
    return _ja(conn, osoba_id, p.osoba_id)
