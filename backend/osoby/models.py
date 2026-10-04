from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
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

    role_casomeric = models.BooleanField(
        "časoměřič / věž",
        default=False,
        help_text="Smí zakládat a opravovat lety všech, uzavírat den.",
    )
    role_ucetni = models.BooleanField(
        "účetní", default=False, help_text="Opravuje lety, uzavírá měsíc, exportuje."
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
