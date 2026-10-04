from django.contrib.auth import authenticate, login, logout, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth
from ninja.utils import check_csrf

from provoz.models import Nastaveni

from . import ucty
from .models import Osoba

router = Router(tags=["přihlášení"])


def over_csrf(request):
    """Ochrana proti podvrženým požadavkům i u volání bez přihlášení."""
    if check_csrf(request) is not None:
        raise HttpError(403, "Neplatný bezpečnostní token, obnovte stránku.")


class Role(Schema):
    admin: bool
    casomeric: bool
    ucetni: bool


class Zastupce(Schema):
    id: int
    jmeno: str


class JaOut(Schema):
    prihlasen: bool
    id: int | None = None
    jmeno: str = ""
    prijmeni: str = ""
    email: str | None = None
    role: Role | None = None
    zastupce: Zastupce | None = None
    testovaci_provoz: bool


def _ja(request) -> dict:
    nastaveni = Nastaveni.aktualni()
    uzivatel = request.user
    if not uzivatel.is_authenticated:
        return {"prihlasen": False, "testovaci_provoz": nastaveni.testovaci_provoz}
    zastupce = None
    if zastupce_id := request.session.get(ucty.SESSION_ZASTUPCE):
        admin = Osoba.objects.filter(pk=zastupce_id).first()
        if admin:
            zastupce = {"id": admin.pk, "jmeno": admin.get_full_name()}
    return {
        "prihlasen": True,
        "id": uzivatel.pk,
        "jmeno": uzivatel.jmeno,
        "prijmeni": uzivatel.prijmeni,
        "email": uzivatel.email,
        "role": {
            "admin": uzivatel.is_staff,
            "casomeric": uzivatel.role_casomeric,
            "ucetni": uzivatel.role_ucetni,
        },
        "zastupce": zastupce,
        "testovaci_provoz": nastaveni.testovaci_provoz,
    }


@router.get("/ja", response=JaOut, summary="Kdo jsem a jaké mám role")
def ja(request):
    get_token(request)  # nastaví cookie s CSRF tokenem pro další volání
    return _ja(request)


class PrihlaseniIn(Schema):
    email: str
    heslo: str
    zapamatovat: bool = True


@router.post("/prihlasit", response=JaOut, summary="Přihlášení e-mailem a heslem")
def prihlasit(request, data: PrihlaseniIn):
    over_csrf(request)
    if ucty.prilis_mnoho_pokusu(request, data.email):
        raise HttpError(429, "Příliš mnoho neúspěšných pokusů. Zkuste to za 15 minut.")
    osoba = authenticate(request, email=data.email.strip().lower(), password=data.heslo)
    if osoba is None:
        ucty.zaznamenat_neuspech(request, data.email)
        raise HttpError(401, "Nesprávný e-mail nebo heslo.")
    ucty.vynulovat_pokusy(request, data.email)
    login(request, osoba)
    if not data.zapamatovat:
        request.session.set_expiry(0)  # odhlásí se po zavření prohlížeče
    return _ja(request)


@router.post("/odhlasit", response=JaOut, auth=django_auth, summary="Odhlášení")
def odhlasit(request):
    logout(request)
    return _ja(request)


class EmailIn(Schema):
    email: str


class ZpravaOut(Schema):
    zprava: str


@router.post("/zapomenute-heslo", response=ZpravaOut, summary="Poslat odkaz pro nové heslo")
def zapomenute_heslo(request, data: EmailIn):
    over_csrf(request)
    ucty.poslat_obnovu_hesla(data.email)
    return {"zprava": "Pokud je e-mail v aplikaci, poslali jsme na něj odkaz pro nové heslo."}


class NoveHesloIn(Schema):
    uid: str
    token: str
    heslo: str


def _osoba_z_odkazu(uid: str, token: str) -> Osoba:
    try:
        osoba = Osoba.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
    except Osoba.DoesNotExist, ValueError, TypeError, OverflowError:
        osoba = None
    if osoba is None or not default_token_generator.check_token(osoba, token):
        raise HttpError(400, "Odkaz je neplatný nebo vypršel. Požádejte o nový.")
    return osoba


@router.get("/nastavit-heslo/{uid}/{token}", response=ZpravaOut, summary="Ověření odkazu")
def overit_odkaz(request, uid: str, token: str):
    osoba = _osoba_z_odkazu(uid, token)
    return {"zprava": osoba.email}


@router.post("/nastavit-heslo", response=JaOut, summary="Nastavení hesla z odkazu")
def nastavit_heslo(request, data: NoveHesloIn):
    over_csrf(request)
    osoba = _osoba_z_odkazu(data.uid, data.token)
    try:
        password_validation.validate_password(data.heslo, osoba)
    except ValidationError as e:
        raise HttpError(400, " ".join(e.messages)) from e
    osoba.set_password(data.heslo)
    osoba.save(update_fields=["password"])
    login(request, osoba, backend="django.contrib.auth.backends.ModelBackend")
    return _ja(request)


@router.post("/vratit-se", response=JaOut, auth=django_auth, summary="Konec „Přihlásit se jako“")
def vratit_se(request):
    if ucty.vratit_se(request) is None:
        raise HttpError(400, "Nejste přihlášen jako jiná osoba.")
    return _ja(request)
