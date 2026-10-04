from datetime import date

from django.contrib.auth import authenticate, login, logout, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth
from ninja.utils import check_csrf

from lety import audit
from provoz import push
from provoz.models import Nastaveni, PushOdber

from . import ucty
from .models import (
    KVALIFIKACE_LICENCE,
    DruhKvalifikace,
    Kvalifikace,
    Licence,
    Medical,
    Osoba,
    TridaMedicalu,
    TypLicence,
)

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


# --- upozornění na zařízení (Web Push) -------------------------------------------------


class PushStavOut(Schema):
    klic: str
    zarizeni: int


class PushKlice(Schema):
    p256dh: str
    auth: str


class PushIn(Schema):
    endpoint: str
    keys: PushKlice
    zarizeni: str = ""


class EndpointIn(Schema):
    endpoint: str


class PocetOut(Schema):
    pocet: int


@router.get("/push", response=PushStavOut, auth=django_auth, summary="Klíč a počet zařízení")
def push_stav(request):
    return {"klic": push.verejny_klic(), "zarizeni": request.user.push_odbery.count()}


@router.post("/push", response=PushStavOut, auth=django_auth, summary="Zapnout upozornění")
def push_zapnout(request, data: PushIn):
    if request.session.get(ucty.SESSION_ZASTUPCE):
        raise HttpError(400, "Při „Přihlásit se jako“ upozornění nezapínejte – patří té osobě.")
    if not data.endpoint.startswith("https://"):
        raise HttpError(400, "Neplatná adresa push služby.")
    # Zařízení, které dřív patřilo jinému uživateli, teď patří přihlášenému.
    PushOdber.objects.update_or_create(
        endpoint=data.endpoint,
        defaults={
            "osoba": request.user,
            "p256dh": data.keys.p256dh,
            "auth": data.keys.auth,
            "zarizeni": data.zarizeni[:200],
        },
    )
    return push_stav(request)


@router.post("/push/vypnout", response=PushStavOut, auth=django_auth, summary="Vypnout")
def push_vypnout(request, data: EndpointIn):
    PushOdber.objects.filter(osoba=request.user, endpoint=data.endpoint).delete()
    return push_stav(request)


@router.post("/push/zkouska", response=PocetOut, auth=django_auth, summary="Zkušební upozornění")
def push_zkouska(request):
    pocet = push.poslat(
        request.user,
        "LKKL Log – zkouška",
        "Upozornění na tomto zařízení fungují.",
        znacka="zkouska",
    )
    return {"pocet": pocet}


# --- licence a medical (etapa 12) ----------------------------------------------------------
# Pilot spravuje své, admin všechny (v administraci).


class Volba(Schema):
    hodnota: str
    nazev: str


class KvalifikaceIO(Schema):
    druh: str
    platnost_do: date | None = None


class LicenceOut(Schema):
    id: int
    typ: str
    cislo: str
    poznamka: str
    kvalifikace: list[KvalifikaceIO]


class MedicalOut(Schema):
    id: int
    trida: str
    platnost_do: date


class LicenceStavOut(Schema):
    licence: list[LicenceOut]
    medicaly: list[MedicalOut]
    typy: list[Volba]
    kvalifikace: dict[str, list[Volba]]
    tridy: list[Volba]


class LicenceIn(Schema):
    id: int | None = None
    typ: str
    cislo: str = ""
    poznamka: str = ""
    kvalifikace: list[KvalifikaceIO] = []


class MedicalIn(Schema):
    id: int | None = None
    trida: str
    platnost_do: date


def _volby(choices) -> list[dict]:
    return [{"hodnota": h, "nazev": n} for h, n in choices]


def _licence_stav(osoba: Osoba) -> dict:
    nazvy = dict(DruhKvalifikace.choices)
    return {
        "licence": [
            {
                "id": lic.pk,
                "typ": lic.typ,
                "cislo": lic.cislo,
                "poznamka": lic.poznamka,
                "kvalifikace": [
                    {"druh": k.druh, "platnost_do": k.platnost_do}
                    for k in lic.kvalifikace.order_by("id")
                ],
            }
            for lic in osoba.licence.prefetch_related("kvalifikace")
        ],
        "medicaly": list(osoba.medicaly.all()),
        "typy": _volby(TypLicence.choices),
        "kvalifikace": {
            typ: [{"hodnota": d, "nazev": nazvy[d]} for d in druhy]
            for typ, druhy in KVALIFIKACE_LICENCE.items()
        },
        "tridy": _volby(TridaMedicalu.choices),
    }


@router.get("/licence", response=LicenceStavOut, auth=django_auth, summary="Moje licence")
def moje_licence(request):
    return _licence_stav(request.user)


@router.post("/licence", response=LicenceStavOut, auth=django_auth, summary="Uložit licenci")
def ulozit_licenci(request, data: LicenceIn):
    osoba = request.user
    if data.typ not in TypLicence.values:
        raise HttpError(400, "Neznámý typ licence.")
    povolene = KVALIFIKACE_LICENCE[data.typ]
    druhy = [k.druh for k in data.kvalifikace]
    if any(d not in povolene for d in druhy) or len(set(druhy)) != len(druhy):
        raise HttpError(400, "Kvalifikace k tomuto typu licence nepatří.")
    try:
        with transaction.atomic():
            if data.id:
                licence = Licence.objects.filter(pk=data.id, osoba=osoba).first()
                if licence is None:
                    raise HttpError(404, "Licence neexistuje.")
                licence.typ = data.typ
            else:
                licence = Licence(osoba=osoba, typ=data.typ)
            licence.cislo = data.cislo.strip()[:40]
            licence.poznamka = data.poznamka.strip()[:200]
            licence.save()
            licence.kvalifikace.all().delete()
            Kvalifikace.objects.bulk_create(
                [
                    Kvalifikace(licence=licence, druh=k.druh, platnost_do=k.platnost_do)
                    for k in data.kvalifikace
                ]
            )
    except IntegrityError as e:
        raise HttpError(400, "Tento typ licence už máte zadaný.") from e
    audit.zapsat(
        request.user,
        "licence",
        "osoba",
        osoba.pk,
        zmeny={
            "typ": data.typ,
            "kvalifikace": [[k.druh, str(k.platnost_do or "")] for k in data.kvalifikace],
        },
    )
    return _licence_stav(osoba)


@router.post("/licence/{licence_id}/smazat", response=LicenceStavOut, auth=django_auth)
def smazat_licenci(request, licence_id: int):
    smazano, _ = Licence.objects.filter(pk=licence_id, osoba=request.user).delete()
    if smazano:
        audit.zapsat(request.user, "licence_smazana", "osoba", request.user.pk)
    return _licence_stav(request.user)


@router.post("/medical", response=LicenceStavOut, auth=django_auth, summary="Uložit medical")
def ulozit_medical(request, data: MedicalIn):
    osoba = request.user
    if data.trida not in TridaMedicalu.values:
        raise HttpError(400, "Neznámá třída medicalu.")
    try:
        with transaction.atomic():
            if data.id:
                medical = Medical.objects.filter(pk=data.id, osoba=osoba).first()
                if medical is None:
                    raise HttpError(404, "Medical neexistuje.")
            else:
                medical = Medical(osoba=osoba)
            medical.trida = data.trida
            medical.platnost_do = data.platnost_do
            medical.save()
    except IntegrityError as e:
        raise HttpError(400, "Medical této třídy už máte zadaný – upravte ho.") from e
    audit.zapsat(
        request.user,
        "medical",
        "osoba",
        osoba.pk,
        zmeny={"trida": data.trida, "platnost_do": str(data.platnost_do)},
    )
    return _licence_stav(osoba)


@router.post("/medical/{medical_id}/smazat", response=LicenceStavOut, auth=django_auth)
def smazat_medical(request, medical_id: int):
    smazano, _ = Medical.objects.filter(pk=medical_id, osoba=request.user).delete()
    if smazano:
        audit.zapsat(request.user, "medical_smazan", "osoba", request.user.pk)
    return _licence_stav(request.user)
