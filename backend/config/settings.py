"""Nastavení Django projektu LKKL Log.

Vše, co se liší mezi počítačem vývojáře a serverem (hesla, adresy), se čte
z proměnných prostředí. Na serveru je dodá soubor `.env`, lokálně
`backend/.env` (vzor je v `.env.example`).
"""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes", "ano")


def env_list(name: str, default: str = "") -> list[str]:
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


# Lokálně se proměnné načtou z backend/.env (na serveru je předá Docker Compose).
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _value = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _value.strip())

DEBUG = env_bool("DJANGO_DEBUG")
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("Chybí DJANGO_SECRET_KEY (viz .env.example).")
    SECRET_KEY = "dev-only-insecure-key"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
# Vite při vývoji přeposílá API s jiným Host než Origin – jeho adresy jsou důvěryhodné.
_VITE = "http://localhost:5173,http://127.0.0.1:5173" if DEBUG else ""
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", _VITE)

# Číslo verze: soubor VERZE vytváří nasazení z GitHub Actions, jinak „dev“.
_soubor_verze = BASE_DIR / "VERZE"
APP_VERSION = (
    _soubor_verze.read_text(encoding="utf-8").strip()
    if _soubor_verze.exists()
    else os.environ.get("APP_VERSION", "dev")
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "osoby",
    "lety",
    "provoz",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"


# Sestavený React frontend: v Docker image vedle backendu (frontend_dist), při vývoji
# frontend/dist. Proměnná FRONTEND_DIST se použije, jen pokud složka opravdu existuje
# (VPS Centrum si pamatuje proměnné ze starších verzí image).
def najdi_frontend() -> Path:
    kandidati = [
        Path(os.environ["FRONTEND_DIST"]) if os.environ.get("FRONTEND_DIST") else None,
        BASE_DIR / "frontend_dist",
        BASE_DIR.parent / "frontend" / "dist",
    ]
    for cesta in kandidati:
        if cesta and (cesta / "index.html").exists():
            return cesta
    return BASE_DIR.parent / "frontend" / "dist"


FRONTEND_DIST = najdi_frontend()

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


def databaze_z_vps_centra() -> dict | None:
    """Databáze přiřazená ve VPS Centru: přijde jako DB_HOST/DB_USER/DB_NAME/DB_SOCKET.

    Připojení jde přes unixový socket bez hesla (PostgreSQL ověří uživatele podle
    systémového účtu, pod kterým kontejner běží).
    """
    if not os.environ.get("DB_NAME"):
        return None
    host = os.environ.get("DB_SOCKET") or os.environ.get("DB_HOST", "")
    port = ""
    # DB_SOCKET může být cesta k souboru socketu (…/.s.PGSQL.5432) – psycopg chce složku.
    if "/.s.PGSQL." in host:
        host, port = host.rsplit("/.s.PGSQL.", 1)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": host,
        "PORT": port,
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }


DATABASES = {
    "default": databaze_z_vps_centra()
    or dj_database_url.config(
        default="postgres://lkkllog:lkkllog@127.0.0.1:5432/lkkllog",
        conn_max_age=60,
        conn_health_checks=True,
    )
}
# Bez časového limitu by se aplikace při nedostupné databázi zasekla.
DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = 5

# Vlastní tabulka uživatelů – musí být nastavená od první migrace.
AUTH_USER_MODEL = "osoby.Osoba"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Adresa aplikace pro odkazy v e-mailech (pozvánka, zapomenuté heslo).
APP_URL = os.environ.get("APP_URL", "http://localhost:5173").rstrip("/")

# Odkaz pro nastavení hesla (pozvánka i zapomenuté heslo) platí 7 dní.
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 * 7

# Přihlášení vydrží na zařízení ~6 měsíců (pilot nic nevyplňuje při startu).
SESSION_COOKIE_AGE = 60 * 60 * 24 * 180
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# E-mail: bez nastaveného SMTP serveru se e-maily jen vypisují do logu.
# Co se smí odeslat, navíc hlídá režim v nastavení aplikace (provoz.Nastaveni).
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "LKKL Log <info@lkkl.cz>")
_email_port = int(os.environ.get("EMAIL_PORT", "465"))
MAILERS = {
    "default": (
        {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {
                "host": os.environ["EMAIL_HOST"],
                "port": _email_port,
                "username": os.environ.get("EMAIL_HOST_USER", ""),
                "password": os.environ.get("EMAIL_HOST_PASSWORD", ""),
                "use_ssl": _email_port == 465,
                "use_tls": _email_port == 587,
                "timeout": 15,
            },
        }
        if os.environ.get("EMAIL_HOST")
        else {"BACKEND": "django.core.mail.backends.console.EmailBackend"}
    )
}

LANGUAGE_CODE = "cs"
# Vše se ukládá a počítá v UTC (letecký standard).
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
# Soubory frontendu (JS, CSS, ikony) servíruje WhiteNoise přímo z kořene webu.
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None
# Manifest aplikace (instalace na plochu) musí mít správný typ, jinak ho prohlížeč odmítne.
WHITENOISE_MIMETYPES = {".webmanifest": "application/manifest+json"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Domovské letiště – souřadnice pro výpočet západu slunce a soumraku.
LETISTE_SOURADNICE = (50.134, 14.087)  # LKKL Kladno – přibližně, ověřit podle AIP

if not DEBUG:
    # Aplikace běží za nginx (a Cloudflare), které ukončují HTTPS.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
