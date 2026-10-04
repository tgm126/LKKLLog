from datetime import timedelta

import pytest
from django.utils import timezone

from lety.models import AuditLog, StavLetu, Ucel

from .pomocne import normalni, post, ve_vzduchu

pytestmark = pytest.mark.django_db


def ukonceny(svet, klient, **kw):
    ted = timezone.now().replace(microsecond=0)
    data = normalni(
        svet,
        akce="dopsat",
        cas_vzletu=(ted - timedelta(hours=2)).isoformat(),
        cas_pristani=(ted - timedelta(hours=1)).isoformat(),
        **kw,
    )
    return post(klient, "/api/lety", data).json()


def oprava(let, **zmeny):
    """Data pro opravu = současný stav letu + změny."""
    data = {
        "letadlo_id": let["letadlo_id"],
        "ucel": let["ucel"],
        "posadka": [{"osoba_id": p["osoba_id"], "funkce": p["funkce"]} for p in let["posadka"]],
        "uloha_id": let["uloha_id"],
        "zpusob_vzletu": let["zpusob_vzletu"],
        "misto_vzletu_id": let["misto_vzletu_id"],
        "pocet_hostu": let["pocet_hostu"],
        "platce_id": let["platce_id"],
        "plati_aeroklub": let["plati_aeroklub"],
        "cas_vzletu": let["cas_vzletu"],
        "cas_pristani": let["cas_pristani"],
        "misto_pristani_id": let["misto_pristani_id"],
        "pocet_tg": let["pocet_tg"],
        "verze": let["verze"],
        "duvod": "chybny_cas",
    }
    data.update(zmeny)
    return data


def test_oprava_casu_prepocita_dobu_a_zapise_historii(jako, svet):
    klient = jako(svet.pilot)
    let = ukonceny(svet, klient)
    assert let["doba_min"] == 60
    nove = (timezone.now().replace(microsecond=0) - timedelta(minutes=30)).isoformat()
    odpoved = post(
        klient,
        f"/api/lety/{let['id']}/oprava",
        oprava(let, cas_pristani=nove, duvod="zapomenuty_stop", poznamka="Zapomněl jsem."),
    )
    assert odpoved.status_code == 200, odpoved.json()
    assert odpoved.json()["doba_min"] == 90
    assert odpoved.json()["verze"] == let["verze"] + 1

    zaznam = AuditLog.objects.get(akce="oprava", objekt_id=let["id"])
    assert list(zaznam.zmeny) == ["přistání"]
    assert zaznam.duvod == "zapomenuty_stop"
    historie = klient.get(f"/api/lety/{let['id']}/historie").json()
    assert [h["akce"] for h in historie] == ["Založení", "Oprava"]
    assert historie[1]["duvod"] == "Zapomenutý stop"
    assert historie[1]["poznamka"] == "Zapomněl jsem."


def test_soubezna_oprava_neprepise_cizi_zmenu(jako, svet):
    let = ukonceny(svet, jako(svet.pilot))
    prvni = oprava(let, pocet_tg=2)
    assert post(jako(svet.casomeric), f"/api/lety/{let['id']}/oprava", prvni).status_code == 200
    # Druhý uživatel má stále starou verzi.
    druha = post(jako(svet.pilot), f"/api/lety/{let['id']}/oprava", oprava(let, pocet_tg=5))
    assert druha.status_code == 409
    assert druha.json()["kod"] == "zmeneno"
    assert "Test Časoměřič" in druha.json()["detail"]


def test_oprava_vyzaduje_duvod_a_zmenu(jako, svet):
    klient = jako(svet.pilot)
    let = ukonceny(svet, klient)
    url = f"/api/lety/{let['id']}/oprava"
    assert post(klient, url, oprava(let, duvod="")).status_code == 400
    odpoved = post(klient, url, oprava(let))
    assert odpoved.status_code == 400
    assert "Nic se nezměnilo" in odpoved.json()["detail"]


def test_oprava_hlida_pravidla_a_prava(jako, svet):
    let = ukonceny(svet, jako(svet.pilot))
    url = f"/api/lety/{let['id']}/oprava"
    assert post(jako(svet.cizi_pilot), url, oprava(let, pocet_tg=1)).status_code == 403
    assert post(jako(svet.casomeric), url, oprava(let, ucel=Ucel.VYCVIK)).status_code == 400
    zmena_posadky = oprava(
        let,
        duvod="chybna_osoba",
        posadka=[{"osoba_id": svet.instruktor.pk, "funkce": "pic"}],
        platce_id=None,
    )
    odpoved = post(jako(svet.casomeric), url, zmena_posadky)
    assert odpoved.status_code == 200
    assert odpoved.json()["platce"] == "Test Instruktor"


def test_oprava_nesmi_vytvorit_prekryv(jako, svet):
    klient = jako(svet.pilot)
    prvni = ukonceny(svet, klient)
    ted = timezone.now().replace(microsecond=0)
    druhy = post(
        klient,
        "/api/lety",
        normalni(
            svet,
            akce="dopsat",
            cas_vzletu=(ted - timedelta(minutes=50)).isoformat(),
            cas_pristani=(ted - timedelta(minutes=20)).isoformat(),
        ),
    ).json()
    # Přistání prvního letu posunuté do doby druhého letu → stejné letadlo i pilot.
    odpoved = post(
        klient,
        f"/api/lety/{prvni['id']}/oprava",
        oprava(prvni, cas_pristani=(ted - timedelta(minutes=40)).isoformat()),
    )
    assert odpoved.status_code == 409
    assert druhy["id"]


def test_let_ve_vzduchu_nejde_ukoncit_opravou(jako, svet):
    let = post(jako(svet.pilot), "/api/lety", normalni(svet)).json()
    odpoved = post(
        jako(svet.pilot),
        f"/api/lety/{let['id']}/oprava",
        oprava(let, cas_pristani=timezone.now().isoformat()),
    )
    assert odpoved.status_code == 400


# --- Zpět ------------------------------------------------------------------------


def test_zpet_po_pristani_vrati_let_do_vzduchu(jako, svet):
    let = ve_vzduchu(svet)
    klient = jako(svet.casomeric)
    ukonceny_let = post(klient, f"/api/lety/{let.pk}/pristani").json()
    zpet = post(klient, f"/api/lety/{let.pk}/zpet", {"verze": ukonceny_let["verze"]}).json()
    assert zpet["stav"] == StavLetu.VE_VZDUCHU and zpet["cas_pristani"] is None


def test_zpet_po_vzletu_a_po_zalozeni(jako, svet):
    klient = jako(svet.pilot)
    pripraveny = post(klient, "/api/lety", normalni(svet, akce="pripravit")).json()
    po_vzletu = post(klient, f"/api/lety/{pripraveny['id']}/vzlet").json()
    zpet = post(klient, f"/api/lety/{pripraveny['id']}/zpet", {"verze": po_vzletu["verze"]})
    assert zpet.json()["stav"] == StavLetu.PRIPRAVEN

    omyl = post(klient, "/api/lety", normalni(svet, letadlo_id=svet.dvoumistne.pk)).json()
    zpet = post(klient, f"/api/lety/{omyl['id']}/zpet", {"verze": omyl["verze"]}).json()
    assert zpet["stav"] == StavLetu.ZRUSEN and zpet["duvod_zruseni"] == "omyl"


def test_zpet_jen_autor_a_jen_chvili(jako, svet, monkeypatch):
    let = post(jako(svet.pilot), "/api/lety", normalni(svet)).json()
    url = f"/api/lety/{let['id']}/zpet"
    assert post(jako(svet.casomeric), url, {"verze": let["verze"]}).status_code == 409

    za_chvili = timezone.now() + timedelta(minutes=5)
    monkeypatch.setattr("lety.sluzby.timezone.now", lambda: za_chvili)
    odpoved = post(jako(svet.pilot), url, {"verze": let["verze"]})
    assert odpoved.status_code == 409 and odpoved.json()["kod"] == "nelze"
