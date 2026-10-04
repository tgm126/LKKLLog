"""Push notifikace (Web Push) na zařízení, kde si je osoba zapnula.

Klíč VAPID (podpis serveru vůči push službám prohlížečů) se odvozuje z SECRET_KEY,
takže není potřeba žádné další tajemství. Změna SECRET_KEY zneplatní všechna
přihlášená zařízení – lidé si upozornění zapnou znovu.
"""

import base64
import json
import logging
from functools import cache

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings
from py_vapid import Vapid02
from pywebpush import WebPushException, webpush

from .models import PushOdber

log = logging.getLogger(__name__)

# Řád eliptické křivky P-256 (soukromý klíč musí být 1 … N-1).
_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


@cache
def _soukromy_klic() -> ec.EllipticCurvePrivateKey:
    hkdf = HKDF(algorithm=SHA256(), length=32, salt=b"lkkllog", info=b"vapid")
    cislo = int.from_bytes(hkdf.derive(settings.SECRET_KEY.encode()), "big") % (_N - 1) + 1
    return ec.derive_private_key(cislo, ec.SECP256R1())


def verejny_klic() -> str:
    """Veřejný klíč pro prohlížeč (applicationServerKey) v base64url."""
    surovy = (
        _soukromy_klic()
        .public_key()
        .public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    )
    return base64.urlsafe_b64encode(surovy).rstrip(b"=").decode()


def poslat(osoba, titulek: str, text: str, url: str = "/", znacka: str = "") -> int:
    """Pošle upozornění na všechna zařízení osoby. Vrací počet doručených."""
    data = json.dumps({"titulek": titulek, "text": text, "url": url, "znacka": znacka})
    doruceno = 0
    for odber in PushOdber.objects.filter(osoba=osoba):
        try:
            webpush(
                subscription_info={
                    "endpoint": odber.endpoint,
                    "keys": {"p256dh": odber.p256dh, "auth": odber.auth},
                },
                data=data,
                vapid_private_key=Vapid02(private_key=_soukromy_klic()),
                vapid_claims={"sub": f"mailto:{settings.DEFAULT_FROM_EMAIL}"},
                ttl=6 * 3600,
                timeout=10,
            )
            doruceno += 1
        except WebPushException as e:
            stav = e.response.status_code if e.response is not None else None
            if stav in (404, 410):  # zařízení upozornění zrušilo nebo už neexistuje
                odber.delete()
            else:
                log.warning("Push pro %s se nepodařil: %s", osoba, e)
        except Exception as e:  # síť, timeout… – upozornění nesmí shodit kontrolu letů
            log.warning("Push pro %s se nepodařil: %s", osoba, e)
    return doruceno
