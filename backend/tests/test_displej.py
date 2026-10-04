from datetime import timedelta

import pytest
from django.utils import timezone

from osoby.models import Osoba
from provoz.models import Nastaveni

from .pomocne import let_v, ve_vzduchu

pytestmark = pytest.mark.django_db


@pytest.fixture
def klic(db):
    nastaveni = Nastaveni.aktualni()
    klic = nastaveni.novy_klic_displeje()
    nastaveni.save()
    return klic


def test_displej_bez_prihlaseni_jen_s_klicem(client, svet, klic):
    ve_vzduchu(svet)
    let_v(svet, timezone.now() - timedelta(hours=1), minut=30, pocet_tg=2)

    assert client.get("/api/displej").status_code == 404
    assert client.get("/api/displej?klic=spatny").status_code == 404
    odpoved = client.get(f"/api/displej?klic={klic}")
    assert odpoved.status_code == 200
    data = odpoved.json()
    assert [let["stav"] for let in data["lety"]] == ["ukoncen", "ve_vzduchu"]
    assert data["lety"][1]["posadka"][0]["jmeno"] == "Test Pilot"
    # Na veřejnou obrazovku nepatří plátce ani ovládání.
    assert "platce" not in data["lety"][0] and "muze_ovladat" not in data["lety"][0]
    assert data["souhrn"]["celkem"]["lety"] == 1
    assert data["souhrn"]["celkem"]["pristani"] == 3


def test_vypnuty_displej(client, db):
    assert Nastaveni.aktualni().displej_klic == ""
    assert client.get("/api/displej?klic=").status_code == 404


def test_novy_odkaz_v_administraci_zneplatni_stary(client, klic):
    admin = Osoba.objects.create_superuser("admin@example.com", "x")
    client.force_login(admin)
    url = "/admin/provoz/nastaveni/1/change/"
    stranka = client.get(url)
    assert f"/displej/{klic}" in stranka.text

    data = {"email_rezim": "vypnuto", "povolene_adresy": "", "displej": "novy"}
    assert client.post(url, data).status_code == 302
    novy = Nastaveni.aktualni().displej_klic
    assert len(novy) == 32 and novy != klic
    client.logout()
    assert client.get(f"/api/displej?klic={klic}").status_code == 404
    assert client.get(f"/api/displej?klic={novy}").status_code == 200

    client.force_login(admin)
    client.post(url, {**data, "displej": "vypnout"})
    assert Nastaveni.aktualni().displej_klic == ""
