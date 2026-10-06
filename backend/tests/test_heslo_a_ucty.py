"""Odkaz pro nastavení hesla, změna hesla, správa účtů a „přihlásit se jako“."""

import time

from app import bezpecnost, prikazy
from app.nastaveni import nastaveni
from app.prihlasovani import CHYBA_ODKAZU

from .conftest import HESLO

NOVE = "uplne-nove-heslo"


def _klic(odkaz: str) -> str:
    return odkaz.split("klic=", 1)[1]


def test_pozvanka_nastaveni_hesla_a_jednorazovost(klient, osoba, prihlasit, conn):
    osoba("Admin", admin=True)
    novak = osoba("Novak", heslo=None)
    admin = prihlasit("admin@example.cz")
    odpoved = admin.post(f"/api/ucty/{novak}/pozvanka")
    assert odpoved.status_code == 200
    odkaz = odpoved.json()["odkaz"]
    assert odkaz.startswith("https://lety.test/heslo?klic=")
    k = klient()
    osoba_z_odkazu = k.get("/api/heslo/odkaz", params={"klic": _klic(odkaz)}).json()
    # E-mail kvůli správci hesel (uloží nové heslo ke správnému účtu).
    assert (osoba_z_odkazu["prijmeni"], osoba_z_odkazu["email"]) == ("Novak", "novak@example.cz")
    assert (
        k.post("/api/heslo/nastavit", json={"klic": _klic(odkaz), "heslo": "kratke"}).status_code
        == 400
    )
    odpoved = k.post("/api/heslo/nastavit", json={"klic": _klic(odkaz), "heslo": NOVE})
    assert odpoved.status_code == 200 and odpoved.json()["osoba_id"] == novak
    assert k.get("/api/ja").status_code == 200  # rovnou přihlášen
    # Odkaz je jednorázový.
    znovu = klient().post("/api/heslo/nastavit", json={"klic": _klic(odkaz), "heslo": NOVE})
    assert znovu.status_code == 400 and znovu.json()["detail"] == CHYBA_ODKAZU
    assert klient().get("/api/heslo/odkaz", params={"klic": _klic(odkaz)}).status_code == 400
    assert conn.execute(
        "SELECT pozvanka_odeslana FROM lkkl.ucet WHERE osoba_id = %s", (novak,)
    ).fetchone()["pozvanka_odeslana"]


def test_odkaz_vyprsi_a_nejde_podvrhnout(klient, osoba):
    novak = osoba("Novak", heslo=None)
    stary = bezpecnost.podepsat_odkaz(
        nastaveni.tajny_klic, novak, None, vydano=int(time.time()) - 4 * 24 * 3600
    )
    platny = bezpecnost.podepsat_odkaz(nastaveni.tajny_klic, novak, None)
    k = klient()
    for klic in (stary, platny[:-2] + "xx", f"{novak + 1}.{platny.split('.', 1)[1]}", "nesmysl"):
        assert k.get("/api/heslo/odkaz", params={"klic": klic}).status_code == 400, klic
    assert k.get("/api/heslo/odkaz", params={"klic": platny}).status_code == 200


def test_nastaveni_hesla_odhlasi_ostatni_zarizeni(klient, osoba, prihlasit):
    novak = osoba("Novak")
    jinde = prihlasit("novak@example.cz")
    klic = bezpecnost.podepsat_odkaz(nastaveni.tajny_klic, novak, None)
    assert (
        klient().post("/api/heslo/nastavit", json={"klic": klic, "heslo": NOVE}).status_code == 200
    )
    assert jinde.get("/api/ja").status_code == 401


def test_zmena_hesla(osoba, prihlasit, klient):
    osoba("Novak")
    telefon = prihlasit("novak@example.cz")
    pocitac = prihlasit("novak@example.cz")
    spatne = pocitac.post("/api/heslo/zmenit", json={"stare": "x" * 10, "nove": NOVE})
    assert spatne.status_code == 400
    assert pocitac.post("/api/heslo/zmenit", json={"stare": HESLO, "nove": NOVE}).status_code == 204
    assert telefon.get("/api/ja").status_code == 401
    assert pocitac.get("/api/ja").status_code == 200
    k = klient()
    assert (
        k.post("/api/prihlaseni", json={"email": "novak@example.cz", "heslo": HESLO}).status_code
        == 401
    )
    assert (
        k.post("/api/prihlaseni", json={"email": "novak@example.cz", "heslo": NOVE}).status_code
        == 200
    )


def test_aktivace_osoby(osoba, prihlasit, conn):
    osoba("Admin", admin=True)
    bez_uctu = osoba("Novak", ucet=False)
    bez_emailu = conn.execute(
        "INSERT INTO lkkl.osoba (jmeno, prijmeni) VALUES ('Petr', 'Bezemailu') RETURNING id"
    ).fetchone()["id"]
    admin = prihlasit("admin@example.cz")
    ucet = admin.post("/api/ucty", json={"osoba_id": bez_uctu}).json()
    assert ucet["prijmeni"] == "Novak" and not ucet["ma_heslo"] and not ucet["admin"]
    assert admin.post("/api/ucty", json={"osoba_id": bez_uctu}).status_code == 400
    odpoved = admin.post("/api/ucty", json={"osoba_id": bez_emailu})
    assert odpoved.status_code == 400 and "e-mail" in odpoved.json()["detail"]
    assert admin.post("/api/ucty", json={"osoba_id": 999999}).status_code == 404
    assert {u["prijmeni"] for u in admin.get("/api/ucty").json()} == {"Admin", "Novak"}


def test_jen_admin_spravuje_ucty(osoba, prihlasit):
    novak = osoba("Novak", smi_odblokovat=True)
    k = prihlasit("novak@example.cz")
    assert k.get("/api/ucty").status_code == 403
    assert k.post("/api/ucty", json={"osoba_id": novak}).status_code == 403
    assert k.post(f"/api/ucty/{novak}", json={"admin": True}).status_code == 403
    assert k.post(f"/api/ucty/{novak}/pozvanka").status_code == 403


def test_zablokovani_uctu_adminem(osoba, prihlasit):
    admin_id = osoba("Admin", admin=True)
    novak = osoba("Novak")
    zarizeni = prihlasit("novak@example.cz")
    admin = prihlasit("admin@example.cz")
    ucet = admin.post(f"/api/ucty/{novak}", json={"aktivni": False}).json()
    assert not ucet["smi_se_prihlasit"]
    assert zarizeni.get("/api/ja").status_code == 401
    assert admin.post(f"/api/ucty/{novak}/pozvanka").status_code == 400
    # Sám sobě admin účet nezablokuje ani admina neodebere.
    assert admin.post(f"/api/ucty/{admin_id}", json={"aktivni": False}).status_code == 400
    assert admin.post(f"/api/ucty/{admin_id}", json={"admin": False}).status_code == 400
    assert admin.post(f"/api/ucty/{novak}", json={"aktivni": True}).json()["smi_se_prihlasit"]


def test_prihlasit_se_jako(osoba, prihlasit):
    admin_id = osoba("Admin", admin=True)
    osoba("Druhyadmin", admin=True)
    novak = osoba("Novak")
    admin = prihlasit("admin@example.cz")
    ja = admin.post(f"/api/prihlasit-jako/{novak}").json()
    assert ja["osoba_id"] == novak and ja["puvodni"]["osoba_id"] == admin_id
    assert not ja["prava"]["admin"]
    # Chová se jako Novák: na správu účtů nemá právo, heslo měnit nesmí.
    assert admin.get("/api/ucty").status_code == 403
    assert admin.post("/api/heslo/zmenit", json={"stare": HESLO, "nove": NOVE}).status_code == 403
    ja = admin.post("/api/prihlasit-jako/konec").json()
    assert ja["osoba_id"] == admin_id and ja["puvodni"] is None
    assert admin.get("/api/ucty").status_code == 200


def test_prihlasit_se_jako_omezeni(osoba, prihlasit):
    osoba("Admin", admin=True)
    druhy = osoba("Druhyadmin", admin=True)
    novak = osoba("Novak")
    admin = prihlasit("admin@example.cz")
    assert admin.post(f"/api/prihlasit-jako/{druhy}").status_code == 400
    assert admin.post("/api/prihlasit-jako/konec").status_code == 400
    pilot = prihlasit("novak@example.cz")
    assert pilot.post(f"/api/prihlasit-jako/{novak}").status_code == 403


def test_odebrani_admina_ukonci_prihlaseni_jako(osoba, prihlasit, conn):
    admin_id = osoba("Admin", admin=True)
    novak = osoba("Novak")
    admin = prihlasit("admin@example.cz")
    admin.post(f"/api/prihlasit-jako/{novak}")
    conn.execute("UPDATE lkkl.ucet SET admin = false WHERE osoba_id = %s", (admin_id,))
    assert admin.get("/api/ja").status_code == 401


def test_prikazy_odkaz_a_uklid(osoba, conn):
    novak = osoba("Novak", heslo=None)
    odkaz = prikazy.odkaz(conn, "NOVAK@example.cz")
    assert bezpecnost.osoba_z_odkazu(_klic(odkaz)) == novak
    conn.execute(
        """INSERT INTO lkkl.relace (id, osoba_id, vytvorena, plati_do)
           VALUES (repeat('a', 64), %s, now() - interval '40 days', now() - interval '1 day')""",
        (novak,),
    )
    assert prikazy.uklid(conn) == 1
