"""Otisky hesel, klíče relací a podepsané odkazy pro nastavení hesla."""

import base64
import hashlib
import hmac
import secrets
import time
from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

PLATNOST_ODKAZU_S = 3 * 24 * 3600
DELKA_HESLA = (10, 128)

_hasher = PasswordHasher()  # argon2id
# Ověřuje se i u neexistujícího účtu, aby odpověď trvala stejně dlouho.
_FIKTIVNI_OTISK = _hasher.hash(secrets.token_urlsafe(16))


def otisk_hesla(heslo: str) -> str:
    return _hasher.hash(heslo)


def over_heslo(otisk: str | None, heslo: str) -> bool:
    try:
        return _hasher.verify(otisk or _FIKTIVNI_OTISK, heslo) and otisk is not None
    except VerificationError, InvalidHashError:
        return False


def potrebuje_novy_otisk(otisk: str) -> bool:
    return _hasher.check_needs_rehash(otisk)


def heslo_ma_spravnou_delku(heslo: str) -> bool:
    return DELKA_HESLA[0] <= len(heslo) <= DELKA_HESLA[1]


def novy_klic_relace() -> tuple[str, str]:
    """Náhodný klíč do cookie a jeho otisk do databáze."""
    klic = secrets.token_urlsafe(32)
    return klic, otisk_klice(klic)


def otisk_klice(klic: str) -> str:
    return hashlib.sha256(klic.encode()).hexdigest()


# --- odkaz pro nastavení hesla ---------------------------------------------------------------
# Tvar: <osoba_id>.<vydáno (unix čas)>.<podpis>. Podpis zahrnuje čas poslední změny hesla,
# takže po nastavení hesla odkaz (i všechny starší) přestane platit.


def _podpis(tajny_klic: str, data: str, heslo_zmeneno: datetime | None) -> str:
    zmena = heslo_zmeneno.astimezone(UTC).isoformat() if heslo_zmeneno else ""
    zprava = f"odkaz-heslo|{data}|{zmena}".encode()
    digest = hmac.new(tajny_klic.encode(), zprava, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def podepsat_odkaz(
    tajny_klic: str, osoba_id: int, heslo_zmeneno: datetime | None, vydano: int | None = None
) -> str:
    data = f"{osoba_id}.{int(time.time()) if vydano is None else vydano}"
    return f"{data}.{_podpis(tajny_klic, data, heslo_zmeneno)}"


def osoba_z_odkazu(klic: str) -> int | None:
    """Osoba, pro kterou je odkaz vydaný (bez ověření podpisu)."""
    casti = klic.split(".")
    if len(casti) != 3 or not casti[0].isdigit() or not casti[1].isdigit():
        return None
    return int(casti[0])


def odkaz_plati(
    tajny_klic: str, klic: str, heslo_zmeneno: datetime | None, ted: int | None = None
) -> bool:
    if osoba_z_odkazu(klic) is None:
        return False
    osoba, vydano, podpis = klic.split(".")
    stari = (int(time.time()) if ted is None else ted) - int(vydano)
    if not 0 <= stari <= PLATNOST_ODKAZU_S:
        return False
    return hmac.compare_digest(podpis, _podpis(tajny_klic, f"{osoba}.{vydano}", heslo_zmeneno))
