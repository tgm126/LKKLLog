from datetime import timedelta

import pytest
from django.utils import timezone

from lety.models import AuditLog, StavLetu, Ucel

from .pomocne import normalni, post, ve_vzduchu

pytestmark = pytest.mark.django_db


# --- přístup a číselníky ---------------------------------------------------------


def test_bez_prihlaseni_nic(client, svet):
    assert client.get("/api/prehled").status_code == 401
    assert client.get("/api/ciselniky").status_code == 401


def test_ciselniky_bez_telefonu(jako, svet):
    svet.pilot.telefon = "+420000000001"
    svet.pilot.save()
    data = jako(svet.pilot).get("/api/ciselniky").json()
    assert {a["imatrikulace"] for a in data["letadla"]} == {"OK-TCS", "OK-TVA", "OK-T101"}
    assert "telefon" not in data["osoby"][0]
    assert "+420000000001" not in str(data)
    assert data["osnovy"][0]["ulohy"][0]["kod"] == "M2"


# --- založení letu a pravidla -------------------------------------------------------


def test_vzlet_ted(jako, svet):
    odpoved = post(jako(svet.pilot), "/api/lety", normalni(svet))
    assert odpoved.status_code == 200, odpoved.json()
    let = odpoved.json()
    assert let["stav"] == StavLetu.VE_VZDUCHU
    assert let["platce"] == "Test Pilot"
    assert let["misto_vzletu"] == "LKKL"
    assert let["muze_ovladat"] is True
    assert AuditLog.objects.filter(akce="zalozeni", objekt_id=let["id"]).exists()


def test_vycvik_bez_zaka_neprojde(jako, svet):
    data = normalni(svet, ucel=Ucel.VYCVIK)
    odpoved = post(jako(svet.pilot), "/api/lety", data)
    assert odpoved.status_code == 400
    assert "Žák" in odpoved.json()["detail"]


def test_vycvik_plati_zak(jako, svet):
    data = normalni(
        svet,
        ucel=Ucel.VYCVIK,
        uloha_id=svet.uloha.pk,
        posadka=[
            {"osoba_id": svet.instruktor.pk, "funkce": "pic"},
            {"osoba_id": svet.zak.pk, "funkce": "zak"},
        ],
    )
    let = post(jako(svet.instruktor), "/api/lety", data).json()
    assert let["platce"] == "Test Žák"
    assert let["uloha"] == "M2 – Okruhy"


def test_solo_dozor_nezabira_misto(jako, svet):
    data = normalni(
        svet,
        letadlo_id=svet.dvoumistne.pk,
        ucel=Ucel.VYCVIK_SOLO,
        pocet_hostu=1,
        posadka=[
            {"osoba_id": svet.zak.pk, "funkce": "pic"},
            {"osoba_id": svet.instruktor.pk, "funkce": "dozor"},
        ],
    )
    let = post(jako(svet.zak), "/api/lety", data).json()
    assert let["platce"] == "Test Žák"


def test_prilis_mnoho_lidi(jako, svet):
    data = normalni(svet, letadlo_id=svet.dvoumistne.pk, pocet_hostu=2)
    odpoved = post(jako(svet.pilot), "/api/lety", data)
    assert odpoved.status_code == 400
    assert "2 míst" in odpoved.json()["detail"]


def test_externi_jen_jako_pic_pri_prezkouseni(jako, svet):
    prezkouseni = normalni(
        svet,
        ucel=Ucel.PREZKOUSENI,
        posadka=[
            {"osoba_id": svet.externi.pk, "funkce": "pic"},
            {"osoba_id": svet.pilot.pk, "funkce": "prezkouseny"},
        ],
    )
    let = post(jako(svet.pilot), "/api/lety", prezkouseni).json()
    assert let["platce"] == "Test Pilot"

    normalni_let = normalni(
        svet,
        letadlo_id=svet.dvoumistne.pk,
        posadka=[{"osoba_id": svet.externi.pk, "funkce": "pic"}],
    )
    assert post(jako(svet.pilot), "/api/lety", normalni_let).status_code == 400


def test_plati_aeroklub(jako, svet):
    let = post(jako(svet.pilot), "/api/lety", normalni(svet, plati_aeroklub=True)).json()
    assert let["plati_aeroklub"] and let["platce"] is None


def test_uloha_musi_sedet(jako, svet):
    # Úloha je pro výcvik, ne pro normální let.
    odpoved = post(jako(svet.pilot), "/api/lety", normalni(svet, uloha_id=svet.uloha.pk))
    assert odpoved.status_code == 400


def test_kluzak_potrebuje_zpusob_vzletu(jako, svet):
    data = normalni(svet, letadlo_id=svet.kluzak.pk)
    assert post(jako(svet.pilot), "/api/lety", data).status_code == 400
    data["zpusob_vzletu"] = "vlek"
    assert post(jako(svet.pilot), "/api/lety", data).status_code == 400
    data["zpusob_vzletu"] = "navijak"
    assert post(jako(svet.pilot), "/api/lety", data).json()["zpusob_vzletu"] == "navijak"


def test_letadlo_ve_vzduchu_nejde_zalozit_znovu(jako, svet):
    prvni = post(jako(svet.pilot), "/api/lety", normalni(svet)).json()
    data = normalni(svet, posadka=[{"osoba_id": svet.casomeric.pk, "funkce": "pic"}])
    odpoved = post(jako(svet.casomeric), "/api/lety", data)
    assert odpoved.status_code == 409
    assert odpoved.json()["kod"] == "letadlo_obsazeno"
    assert odpoved.json()["let_id"] == prvni["id"]


# --- vzlet, přistání, souběh -------------------------------------------------------


def test_pripraveny_let_a_dvojity_vzlet(jako, svet):
    let = post(jako(svet.pilot), "/api/lety", normalni(svet, akce="pripravit")).json()
    assert let["stav"] == StavLetu.PRIPRAVEN and let["cas_vzletu"] is None

    assert post(jako(svet.pilot), f"/api/lety/{let['id']}/vzlet").status_code == 200
    druhy = post(jako(svet.casomeric), f"/api/lety/{let['id']}/vzlet")
    assert druhy.status_code == 409
    assert druhy.json()["kod"] == "uz_zapsano"
    assert "Test Pilot" in druhy.json()["detail"]


def test_pristani_a_dvojity_stisk(jako, svet):
    let = ve_vzduchu(svet)
    odpoved = post(jako(svet.casomeric), f"/api/lety/{let.pk}/pristani", {"pocet_tg": 3})
    assert odpoved.status_code == 200
    data = odpoved.json()
    assert data["stav"] == StavLetu.UKONCEN
    assert data["doba_min"] == 20 and data["pocet_tg"] == 3
    assert data["misto_pristani"] == "LKKL"

    druhy = post(jako(svet.pilot), f"/api/lety/{let.pk}/pristani")
    assert druhy.status_code == 409
    assert "Test Časoměřič" in druhy.json()["detail"]


def test_cizi_pilot_neovlada_cizi_let(jako, svet):
    let = ve_vzduchu(svet)
    assert post(jako(svet.cizi_pilot), f"/api/lety/{let.pk}/pristani").status_code == 403
    prehled = jako(svet.cizi_pilot).get("/api/prehled").json()
    assert prehled["lety"][0]["muze_ovladat"] is False


def test_kratky_let_vyzaduje_volbu(jako, svet):
    let = ve_vzduchu(svet, minut=0)
    klient = jako(svet.pilot)
    odpoved = post(klient, f"/api/lety/{let.pk}/pristani")
    assert odpoved.status_code == 409 and odpoved.json()["kod"] == "kratky_let"
    odpoved = post(klient, f"/api/lety/{let.pk}/pristani", {"kratky_let": "start_bez_doby"})
    assert odpoved.status_code == 200
    assert odpoved.json()["doba_uctovana_min"] == 0


def test_dopsat_probehly_let(jako, svet):
    ted = timezone.now().replace(microsecond=0)
    data = normalni(
        svet,
        akce="dopsat",
        cas_vzletu=(ted - timedelta(hours=2)).isoformat(),
        cas_pristani=(ted - timedelta(hours=1)).isoformat(),
        misto_pristani_id=svet.teren.pk,
        pocet_tg=2,
    )
    let = post(jako(svet.pilot), "/api/lety", data).json()
    assert let["stav"] == StavLetu.UKONCEN
    assert let["doba_min"] == 60
    assert let["dodatecne"] is True
    assert let["misto_pristani"] == "Mimo letiště"


def test_vzlet_v_budoucnu_neprojde(jako, svet):
    data = normalni(svet, cas_vzletu=(timezone.now() + timedelta(hours=1)).isoformat())
    assert post(jako(svet.pilot), "/api/lety", data).status_code == 400


def test_zruseni(jako, svet):
    let = post(jako(svet.pilot), "/api/lety", normalni(svet, akce="pripravit")).json()
    klient = jako(svet.pilot)
    assert post(klient, f"/api/lety/{let['id']}/zrusit", {"duvod": "nesmysl"}).status_code == 400
    data = post(klient, f"/api/lety/{let['id']}/zrusit", {"duvod": "omyl"}).json()
    assert data["stav"] == StavLetu.ZRUSEN and data["duvod_zruseni"] == "omyl"


def test_prehled_dne(jako, svet):
    ve_vzduchu(svet)
    data = jako(svet.pilot).get("/api/prehled").json()
    assert len(data["lety"]) == 1
    assert data["konec_soumraku"] > data["zapad_slunce"]
    vcera = (timezone.now() - timedelta(days=1)).date().isoformat()
    assert jako(svet.pilot).get(f"/api/prehled?den={vcera}").json()["lety"] == []


def test_ucetni_neridi_provoz_ale_ovlada_sve_lety(jako, svet):
    cizi = ve_vzduchu(svet)
    klient = jako(svet.ucetni)
    assert post(klient, f"/api/lety/{cizi.pk}/pristani").status_code == 403

    vlastni = normalni(
        svet,
        letadlo_id=svet.dvoumistne.pk,
        posadka=[{"osoba_id": svet.ucetni.pk, "funkce": "pic"}],
    )
    let = post(klient, "/api/lety", vlastni).json()
    assert let["muze_ovladat"] is True


# --- jedna osoba nemůže letět dvakrát zároveň ---------------------------------------


def test_pilot_ve_vzduchu_nemuze_vzletnout_znovu(jako, svet):
    ve_vzduchu(svet)  # Pilot letí na OK-TCS
    data = normalni(svet, letadlo_id=svet.dvoumistne.pk)
    odpoved = post(jako(svet.casomeric), "/api/lety", data)
    assert odpoved.status_code == 409
    assert odpoved.json()["kod"] == "osoba_obsazena"
    assert "Test Pilot je právě ve vzduchu na OK-TCS" in odpoved.json()["detail"]


def test_pripravit_jde_vzlet_ne(jako, svet):
    ve_vzduchu(svet)
    klient = jako(svet.casomeric)
    data = normalni(svet, letadlo_id=svet.dvoumistne.pk, akce="pripravit")
    let = post(klient, "/api/lety", data).json()
    assert let["stav"] == StavLetu.PRIPRAVEN
    odpoved = post(klient, f"/api/lety/{let['id']}/vzlet")
    assert odpoved.status_code == 409 and odpoved.json()["kod"] == "osoba_obsazena"


def test_dopsany_let_se_nesmi_kryt(jako, svet):
    ted = timezone.now().replace(microsecond=0)
    klient = jako(svet.pilot)
    prvni = normalni(
        svet,
        akce="dopsat",
        cas_vzletu=(ted - timedelta(hours=3)).isoformat(),
        cas_pristani=(ted - timedelta(hours=2)).isoformat(),
    )
    assert post(klient, "/api/lety", prvni).status_code == 200
    kryje = normalni(
        svet,
        letadlo_id=svet.dvoumistne.pk,
        akce="dopsat",
        cas_vzletu=(ted - timedelta(hours=2, minutes=30)).isoformat(),
        cas_pristani=(ted - timedelta(hours=1)).isoformat(),
    )
    assert post(klient, "/api/lety", kryje).status_code == 409
    navazuje = dict(kryje, cas_vzletu=(ted - timedelta(hours=2)).isoformat())
    assert post(klient, "/api/lety", navazuje).status_code == 200


def test_dozor_na_zemi_se_nepocita(jako, svet):
    # Instruktor dozoruje sólo žáka a zároveň sám letí s jiným pilotem.
    solo = normalni(
        svet,
        letadlo_id=svet.dvoumistne.pk,
        ucel=Ucel.VYCVIK_SOLO,
        posadka=[
            {"osoba_id": svet.zak.pk, "funkce": "pic"},
            {"osoba_id": svet.instruktor.pk, "funkce": "dozor"},
        ],
    )
    assert post(jako(svet.casomeric), "/api/lety", solo).status_code == 200
    vlastni = normalni(svet, posadka=[{"osoba_id": svet.instruktor.pk, "funkce": "pic"}])
    assert post(jako(svet.casomeric), "/api/lety", vlastni).status_code == 200
