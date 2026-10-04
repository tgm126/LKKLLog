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
