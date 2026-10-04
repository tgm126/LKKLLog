from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q


class Kategorie(models.TextChoices):
    """Kategorie letadla. Z ní se odvozuje i kategorie letu."""

    MOTOR = "motor", "Motorové"
    TMG = "tmg", "TMG"
    KLUZAK = "kluzak", "Kluzák"
    UL = "ul", "UL"


class Uroven(models.TextChoices):
    ZAK = "zak", "Žák"
    PILOT = "pilot", "Pilot"
    INSTRUKTOR = "instruktor", "Instruktor"
    EXAMINATOR = "examinator", "Examinátor"


class OsobaManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email=None, password=None, **extra):
        email = self.normalize_email(email) if email else None
        osoba = self.model(email=email, **extra)
        if password:
            osoba.set_password(password)
        else:
            osoba.set_unusable_password()
        osoba.save(using=self._db)
        return osoba

    def create_superuser(self, email, password, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class Osoba(AbstractBaseUser, PermissionsMixin):
    """Člen klubu (případně externí examinátor) a zároveň uživatel aplikace.

    Kdo nemá e-mail, nemůže se přihlásit, ale může být v posádce.
    Admin = `is_staff` (+ `is_superuser`); další role jsou samostatné příznaky.
    """

    jmeno = models.CharField("jméno", max_length=60)
    prijmeni = models.CharField("příjmení", max_length=60)
    email = models.EmailField("e-mail", unique=True, null=True, blank=True)
    telefon = models.CharField(
        "mobil",
        max_length=16,
        blank=True,
        validators=[
            RegexValidator(r"^\+\d{9,15}$", "Telefon v mezinárodním tvaru, např. +420731123456.")
        ],
        help_text="Mezinárodní tvar, např. +420731123456.",
    )

    role_casomeric = models.BooleanField(
        "časoměřič / věž",
        default=False,
        help_text="Smí zakládat a opravovat lety všech, uzavírat den.",
    )
    role_ucetni = models.BooleanField(
        "účetní", default=False, help_text="Opravuje lety, uzavírá měsíc, exportuje."
    )
    role_spravce = models.BooleanField(
        "správce licencí a letadel",
        default=False,
        help_text="Vidí a upravuje licence a medical všech pilotů a termíny letadel.",
    )
    externi = models.BooleanField(
        "externí",
        default=False,
        help_text="Osoba mimo klub (např. examinátor): jen jméno, bez přihlášení a notifikací.",
    )
    testovaci = models.BooleanField(
        "testovací",
        default=False,
        help_text="Účet jen pro zkoušení aplikace. Před spuštěním pro celý klub se smaže.",
    )

    is_active = models.BooleanField(
        "aktivní",
        default=True,
        help_text="Neaktivní osoba se nenabízí ve výběrech a nemůže se přihlásit.",
    )
    is_staff = models.BooleanField("admin", default=False, help_text="Přístup do administrace.")
    vytvoreno = models.DateTimeField("vytvořeno", auto_now_add=True)
    pozvanka_odeslana = models.DateTimeField("pozvánka odeslána", null=True, blank=True)

    objects = OsobaManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["jmeno", "prijmeni"]

    class Meta:
        verbose_name = "osoba"
        verbose_name_plural = "osoby"
        ordering = ["prijmeni", "jmeno"]
        constraints = [
            models.CheckConstraint(
                condition=Q(externi=False) | Q(email__isnull=True),
                name="externi_bez_emailu",
                violation_error_message="Externí osoba nemá e-mail ani přihlášení.",
            ),
        ]

    def __str__(self):
        return f"{self.prijmeni} {self.jmeno}"

    def get_full_name(self):
        return f"{self.jmeno} {self.prijmeni}"

    def get_short_name(self):
        return self.jmeno


class Opravneni(models.Model):
    """Co kdo smí létat. Zatím jen pro řazení lidí ve výběrech, nic neblokuje."""

    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name="opravneni")
    kategorie = models.CharField(max_length=10, choices=Kategorie.choices)
    uroven = models.CharField("úroveň", max_length=12, choices=Uroven.choices)
    platne_do = models.DateField("platné do", null=True, blank=True)

    class Meta:
        verbose_name = "oprávnění"
        verbose_name_plural = "oprávnění"
        constraints = [
            models.UniqueConstraint(
                fields=["osoba", "kategorie", "uroven"], name="opravneni_unikatni"
            ),
        ]

    def __str__(self):
        return f"{self.get_kategorie_display()} – {self.get_uroven_display()}"


# --- licence a medical (etapa 12) ------------------------------------------------------
# Podklady k předpisům: docs/licence-a-rozletanost.md


class TypLicence(models.TextChoices):
    PPL_A = "ppl_a", "PPL(A)"
    LAPL_A = "lapl_a", "LAPL(A)"
    SPL = "spl", "SPL"
    ULL = "ull", "Pilot ULL (LAA ČR)"
    RADIO = "radio", "Radiotelefonista (ČTÚ)"


class DruhKvalifikace(models.TextChoices):
    SEP = "sep", "SEP (land)"
    TMG = "tmg", "TMG"
    NAVIJAK = "navijak", "Naviják / auto"
    VLEK = "vlek", "Aerovlek"
    SAMOSTART = "samostart", "Samostart"
    GUMA = "guma", "Guma (bungee)"
    ULL = "ull", "ULL"
    OFL = "ofl", "Omezený (OFL)"
    VFL = "vfl", "Všeobecný (VFL)"


# Které kvalifikace (třídy, způsoby vzletu) patří ke kterému typu licence.
KVALIFIKACE_LICENCE = {
    TypLicence.PPL_A: [DruhKvalifikace.SEP, DruhKvalifikace.TMG],
    TypLicence.LAPL_A: [DruhKvalifikace.SEP, DruhKvalifikace.TMG],
    TypLicence.SPL: [
        DruhKvalifikace.NAVIJAK,
        DruhKvalifikace.VLEK,
        DruhKvalifikace.SAMOSTART,
        DruhKvalifikace.GUMA,
        DruhKvalifikace.TMG,
    ],
    TypLicence.ULL: [DruhKvalifikace.ULL],
    TypLicence.RADIO: [DruhKvalifikace.OFL, DruhKvalifikace.VFL],
}


class Licence(models.Model):
    """Pilotní průkaz. Zadává ho pilot sám nebo admin."""

    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name="licence")
    typ = models.CharField(max_length=8, choices=TypLicence.choices)
    cislo = models.CharField("číslo průkazu", max_length=40, blank=True)
    poznamka = models.CharField("poznámka", max_length=200, blank=True)
    zmeneno = models.DateTimeField("změněno", auto_now=True)

    class Meta:
        verbose_name = "licence"
        verbose_name_plural = "licence"
        ordering = ["osoba", "typ"]
        constraints = [
            models.UniqueConstraint(fields=["osoba", "typ"], name="licence_jednou"),
        ]

    def __str__(self):
        return f"{self.osoba} – {self.get_typ_display()}"


class Kvalifikace(models.Model):
    """Třída (SEP, TMG), způsob vzletu kluzáku nebo ULL v rámci licence."""

    licence = models.ForeignKey(Licence, on_delete=models.CASCADE, related_name="kvalifikace")
    druh = models.CharField(max_length=10, choices=DruhKvalifikace.choices)
    platnost_do = models.DateField(
        "platnost do",
        null=True,
        blank=True,
        help_text=(
            "U PPL(A) konec platnosti kvalifikace SEP/TMG, u ULL a radiofonního průkazu "
            "platnost průkazu."
        ),
    )

    class Meta:
        verbose_name = "kvalifikace"
        verbose_name_plural = "kvalifikace"
        constraints = [
            models.UniqueConstraint(fields=["licence", "druh"], name="kvalifikace_jednou"),
        ]

    def __str__(self):
        return self.get_druh_display()

    def clean(self):
        if self.licence_id and self.druh not in KVALIFIKACE_LICENCE[self.licence.typ]:
            raise ValidationError(
                f"Kvalifikace {self.get_druh_display()} k licenci "
                f"{self.licence.get_typ_display()} nepatří."
            )


class TridaMedicalu(models.TextChoices):
    T1 = "1", "Třída 1"
    T2 = "2", "Třída 2"
    LAPL = "lapl", "LAPL"


# Které třídy medicalu stačí ke které licenci (radiofonní průkaz medical nepotřebuje).
MEDICAL_LICENCE = {
    TypLicence.PPL_A: [TridaMedicalu.T1, TridaMedicalu.T2],
    TypLicence.LAPL_A: [TridaMedicalu.T1, TridaMedicalu.T2, TridaMedicalu.LAPL],
    TypLicence.SPL: [TridaMedicalu.T1, TridaMedicalu.T2, TridaMedicalu.LAPL],
    TypLicence.ULL: [TridaMedicalu.T1, TridaMedicalu.T2, TridaMedicalu.LAPL],
}


class Medical(models.Model):
    """Platnost medicalu pro jednu třídu. Jedno osvědčení může mít platnost pro víc tříd
    (např. třída 2 a LAPL s jiným datem) – pak jsou to dva záznamy."""

    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name="medicaly")
    trida = models.CharField("třída", max_length=4, choices=TridaMedicalu.choices)
    platnost_do = models.DateField("platnost do")

    class Meta:
        verbose_name = "medical"
        verbose_name_plural = "medicaly"
        ordering = ["osoba", "trida"]
        constraints = [
            models.UniqueConstraint(fields=["osoba", "trida"], name="medical_jednou"),
        ]

    def __str__(self):
        return f"{self.osoba} – {self.get_trida_display()} do {self.platnost_do:%d.%m.%Y}"


def smi_spravovat_licence(osoba) -> bool:
    """Licence a medical všech pilotů a termíny letadel: správce a admin."""
    return osoba.is_staff or osoba.role_spravce
