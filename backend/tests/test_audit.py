"""Kontext auditu: aplikace říká databázi, kdo jedná (db/012_audit.sql)."""

from app import bezpecnost
from app.nastaveni import nastaveni

from .conftest import HESLO


def _audit(conn, tabulka: str = "ucet") -> list[dict]:
    return conn.execute(
        "SELECT kdo, akce, popis FROM lkkl.v_audit WHERE tabulka = %s ORDER BY id", (tabulka,)
    ).fetchall()


def test_akce_admina_se_zapise_jeho_jmenem(osoba, prihlasit, conn):
    osoba("Admin", admin=True)
    novak = osoba("Novak", ucet=False)
    prihlasit("admin@example.cz").post("/api/ucty", json={"osoba_id": novak})
    posledni = _audit(conn)[-1]
    assert posledni["kdo"] == "Jan Admin" and posledni["akce"] == "Aktivace účtu"


def test_zablokovani_po_pokusech_zapise_aplikace(osoba, klient, conn):
    osoba("Novak")
    k = klient()
    for _ in range(5):
        k.post("/api/prihlaseni", json={"email": "novak@example.cz", "heslo": "x" * 10})
    posledni = _audit(conn)[-1]
    assert posledni["kdo"] == "aplikace"
    assert posledni["akce"] == "Zablokování po neúspěšných pokusech"


def test_prihlaseni_do_auditu_nic_nepise(osoba, prihlasit, conn):
    osoba("Novak")
    pred = len(_audit(conn))
    prihlasit("novak@example.cz").get("/api/ja")
    assert len(_audit(conn)) == pred


def test_heslo_odkazem_a_zmena_hesla_zapise_osobu(osoba, klient, prihlasit, conn):
    novak = osoba("Novak", heslo=None)
    klic = bezpecnost.podepsat_odkaz(nastaveni.tajny_klic, novak, None)
    klient().post("/api/heslo/nastavit", json={"klic": klic, "heslo": "nove-heslo-123"})
    assert _audit(conn)[-1] == {"kdo": "Jan Novak", "akce": "Změna hesla", "popis": "změněno heslo"}

    k = prihlasit("novak@example.cz", "nove-heslo-123")
    k.post("/api/heslo/zmenit", json={"stare": "nove-heslo-123", "nove": HESLO})
    assert _audit(conn)[-1]["kdo"] == "Jan Novak"


def test_kontext_po_pozadavku_zmizi(osoba, prihlasit, conn):
    """Spojení se vrací do poolu – další (přímá) změna už nesmí nést jméno z požadavku."""
    novak = osoba("Novak")
    prihlasit("novak@example.cz").get("/api/ja")
    conn.execute("UPDATE lkkl.ucet SET admin = true WHERE osoba_id = %s", (novak,))
    assert _audit(conn)[-1]["kdo"] == "přímo v databázi"
