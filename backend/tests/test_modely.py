from datetime import UTC, datetime, timedelta

import pytest
from django.db import IntegrityError, transaction

from lety.models import AuditLog, FunkcePosadky, Let, Posadka, StavLetu, Ucel
from osoby.models import Osoba

T0 = datetime(2026, 5, 1, 10, 0, 0, tzinfo=UTC)


def novy_let(kluzak, lkkl, pilot, vzlet=T0, pristani=None, **kw):
    kw.setdefault("stav", StavLetu.UKONCEN if pristani else StavLetu.VE_VZDUCHU)
    return Let.objects.create(
        letadlo=kluzak,
        ucel=Ucel.NORMALNI,
        misto_vzletu=lkkl,
        cas_vzletu=vzlet,
        cas_pristani=pristani,
        platce=pilot,
        zalozil=pilot,
        **kw,
    )


@pytest.mark.parametrize(
    ("sekundy", "minuty"),
    [(0, 0), (29, 0), (30, 1), (89, 1), (90, 2), (20 * 60 + 29, 20), (20 * 60 + 30, 21)],
)
def test_doba_letu_se_zaokrouhluje_na_minuty(kluzak, lkkl, pilot, sekundy, minuty):
    let = novy_let(kluzak, lkkl, pilot, pristani=T0 + timedelta(seconds=sekundy))
    let.refresh_from_db()
    assert let.doba_min == minuty


def test_let_ve_vzduchu_nema_dobu(kluzak, lkkl, pilot):
    let = novy_let(kluzak, lkkl, pilot)
    let.refresh_from_db()
    assert let.doba_min is None


def test_pristani_pred_vzletem_neprojde(kluzak, lkkl, pilot):
    with pytest.raises(IntegrityError):
        novy_let(kluzak, lkkl, pilot, pristani=T0 - timedelta(minutes=1))


def test_letadlo_nemuze_mit_dva_prekryvajici_se_lety(kluzak, lkkl, pilot):
    novy_let(kluzak, lkkl, pilot, pristani=T0 + timedelta(minutes=20))
    with pytest.raises(IntegrityError), transaction.atomic():
        novy_let(kluzak, lkkl, pilot, vzlet=T0 + timedelta(minutes=10))
    # Navazující let (vzlet přesně v čase přistání) je v pořádku.
    novy_let(kluzak, lkkl, pilot, vzlet=T0 + timedelta(minutes=20))


def test_let_ve_vzduchu_blokuje_letadlo(kluzak, lkkl, pilot):
    novy_let(kluzak, lkkl, pilot)
    with pytest.raises(IntegrityError):
        novy_let(kluzak, lkkl, pilot, vzlet=T0 + timedelta(hours=3))


def test_zruseny_let_neblokuje_letadlo(kluzak, lkkl, pilot):
    novy_let(
        kluzak,
        lkkl,
        pilot,
        pristani=T0 + timedelta(minutes=20),
        stav=StavLetu.ZRUSEN,
        duvod_zruseni="omyl",
    )
    novy_let(kluzak, lkkl, pilot, vzlet=T0 + timedelta(minutes=5))


def test_plati_bud_osoba_nebo_aeroklub(kluzak, lkkl, pilot):
    with pytest.raises(IntegrityError), transaction.atomic():
        novy_let(kluzak, lkkl, pilot, plati_aeroklub=True)
    let = Let.objects.create(
        letadlo=kluzak, ucel=Ucel.NORMALNI, misto_vzletu=lkkl, plati_aeroklub=True, zalozil=pilot
    )
    assert let.platce is None


def test_jen_jeden_pic(kluzak, lkkl, pilot):
    let = novy_let(kluzak, lkkl, pilot)
    druhy = Osoba.objects.create_user(None, jmeno="Petr", prijmeni="Dvořák")
    Posadka.objects.create(let=let, osoba=pilot, funkce=FunkcePosadky.PIC)
    with pytest.raises(IntegrityError):
        Posadka.objects.create(let=let, osoba=druhy, funkce=FunkcePosadky.PIC)


def test_auditni_log_nejde_zmenit_ani_smazat(pilot):
    zaznam = AuditLog.objects.create(kdo=pilot, akce="test", objekt="let", objekt_id=1)
    with pytest.raises(Exception, match="Auditní log nelze"), transaction.atomic():
        AuditLog.objects.filter(pk=zaznam.pk).update(akce="jina")
    with pytest.raises(Exception, match="Auditní log nelze"), transaction.atomic():
        zaznam.delete()


def test_externi_osoba_nema_email(db):
    with pytest.raises(IntegrityError):
        Osoba.objects.create_user("ext@example.com", jmeno="Karel", prijmeni="Cizí", externi=True)


def test_osoba_bez_emailu_se_neprihlasi(db):
    osoba = Osoba.objects.create_user(None, jmeno="Eva", prijmeni="Malá")
    assert not osoba.has_usable_password()
