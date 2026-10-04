from datetime import date, datetime

from astral import LocationInfo
from astral.sun import sun
from django.conf import settings


def slunce(den: date) -> dict[str, datetime]:
    """Západ slunce a konec občanského soumraku na domovském letišti (UTC)."""
    sirka, delka = settings.LETISTE_SOURADNICE
    misto = LocationInfo("LKKL", "CZ", "UTC", sirka, delka)
    udaje = sun(misto.observer, date=den)
    return {"zapad": udaje["sunset"], "soumrak": udaje["dusk"]}
