from datetime import timedelta

from django.utils import timezone

from lety.models import Let, StavLetu, Ucel
from osoby.models import Osoba


def osoba(prijmeni, **kw):
    return Osoba.objects.create_user(None, jmeno="Test", prijmeni=prijmeni, **kw)


def post(klient, url, data=None):
    return klient.post(url, data or {}, content_type="application/json")


def normalni(svet, **kw):
    data = {
        "letadlo_id": svet.motor.pk,
        "ucel": Ucel.NORMALNI,
        "posadka": [{"osoba_id": svet.pilot.pk, "funkce": "pic"}],
    }
    data.update(kw)
    return data


def ve_vzduchu(svet, minut=20):
    let = Let.objects.create(
        letadlo=svet.motor,
        ucel=Ucel.NORMALNI,
        misto_vzletu=svet.lkkl,
        platce=svet.pilot,
        zalozil=svet.pilot,
        stav=StavLetu.VE_VZDUCHU,
        cas_vzletu=timezone.now().replace(microsecond=0) - timedelta(minutes=minut),
    )
    let.posadka.create(osoba=svet.pilot, funkce="pic")
    return let


def let_v(svet, vzlet, minut=30, letadlo=None, pilot=None, **kw):
    """Ukončený let v daném čase (přímo v databázi, bez kontrol služby)."""
    pilot = pilot or svet.pilot
    kw.setdefault("stav", StavLetu.UKONCEN)
    kw.setdefault("platce", pilot)
    novy = Let.objects.create(
        letadlo=letadlo or svet.motor,
        ucel=kw.pop("ucel", Ucel.NORMALNI),
        misto_vzletu=svet.lkkl,
        misto_pristani=svet.lkkl if kw["stav"] == StavLetu.UKONCEN else None,
        cas_vzletu=vzlet,
        cas_pristani=vzlet + timedelta(minutes=minut) if kw["stav"] == StavLetu.UKONCEN else None,
        zalozil=pilot,
        **kw,
    )
    novy.posadka.create(osoba=pilot, funkce="pic")
    return novy
