"""Účty: pozvánky, zapomenuté heslo, „Přihlásit se jako“ a omezení pokusů o přihlášení."""

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from lety import audit
from provoz.email import odeslat

from .models import Osoba

SESSION_ZASTUPCE = "zastupce_id"
MAX_POKUSU = 5
OKNO_POKUSU = 15 * 60  # sekund


def odkaz_na_heslo(osoba: Osoba) -> str:
    uid = urlsafe_base64_encode(force_bytes(osoba.pk))
    token = default_token_generator.make_token(osoba)
    return f"{settings.APP_URL}/nastavit-heslo/{uid}/{token}"


def poslat_pozvanku(osoba: Osoba, kdo=None) -> bool:
    """Pošle pozvánku s odkazem pro nastavení hesla. Vrací True, pokud odešla."""
    if not osoba.email or osoba.externi or not osoba.is_active:
        return False
    text = (
        f"Dobrý den,\n\n"
        f"byl vám založen účet v aplikaci LKKL Log pro evidenci letů aeroklubu.\n"
        f"Heslo si nastavíte na této adrese (odkaz platí 7 dní):\n\n"
        f"{odkaz_na_heslo(osoba)}\n\n"
        f"Přihlašovat se budete e-mailem {osoba.email}.\n\n"
        f"LKKL Log\n"
    )
    if not odeslat(osoba.email, "Pozvánka do LKKL Log", text):
        return False
    osoba.pozvanka_odeslana = timezone.now()
    osoba.save(update_fields=["pozvanka_odeslana"])
    audit.zapsat(kdo, "pozvanka", "osoba", osoba.pk)
    return True


def poslat_obnovu_hesla(email: str) -> None:
    """Zapomenuté heslo. Navenek se nikdy neprozradí, zda e-mail v aplikaci existuje."""
    osoba = Osoba.objects.filter(email__iexact=email.strip(), is_active=True).first()
    if osoba is None or osoba.externi:
        return
    text = (
        f"Dobrý den,\n\n"
        f"někdo (nejspíš vy) požádal o nové heslo do aplikace LKKL Log.\n"
        f"Nové heslo si nastavíte zde (odkaz platí 7 dní):\n\n"
        f"{odkaz_na_heslo(osoba)}\n\n"
        f"Pokud jste o změnu nežádali, e-mail ignorujte – heslo zůstává beze změny.\n\n"
        f"LKKL Log\n"
    )
    odeslat(osoba.email, "Nastavení hesla – LKKL Log", text)


def prihlasit_jako(request, cil: Osoba) -> None:
    """Admin se přihlásí jako jiná osoba; původní účet si pamatujeme v session."""
    admin = request.user
    zastupce_id = request.session.get(SESSION_ZASTUPCE) or admin.pk
    login(request, cil, backend="django.contrib.auth.backends.ModelBackend")
    request.session[SESSION_ZASTUPCE] = zastupce_id
    audit.zapsat(admin, "prihlaseni_jako", "osoba", cil.pk)


def vratit_se(request) -> Osoba | None:
    """Ukončí „Přihlásit se jako“ a vrátí admina do jeho účtu."""
    zastupce_id = request.session.get(SESSION_ZASTUPCE)
    if not zastupce_id:
        return None
    admin = Osoba.objects.filter(pk=zastupce_id, is_staff=True, is_active=True).first()
    if admin is None:
        return None
    login(request, admin, backend="django.contrib.auth.backends.ModelBackend")
    request.session.pop(SESSION_ZASTUPCE, None)
    audit.zapsat(admin, "prihlaseni_jako_konec", "osoba", admin.pk)
    return admin


def skutecna_ip(request) -> str:
    """IP adresa uživatele za Cloudflare a nginx."""
    return (
        request.META.get("HTTP_CF_CONNECTING_IP")
        or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR", "")
    )


def _klic_pokusu(request, email: str) -> str:
    return f"prihlaseni:{skutecna_ip(request)}:{email.strip().lower()}"


def prilis_mnoho_pokusu(request, email: str) -> bool:
    return cache.get(_klic_pokusu(request, email), 0) >= MAX_POKUSU


def zaznamenat_neuspech(request, email: str) -> None:
    klic = _klic_pokusu(request, email)
    cache.add(klic, 0, OKNO_POKUSU)
    cache.incr(klic)


def vynulovat_pokusy(request, email: str) -> None:
    cache.delete(_klic_pokusu(request, email))
