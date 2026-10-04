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
    provozni_opravneni = models.ManyToManyField(
        "ciselniky.ProvozniOpravneni",
        blank=True,
        related_name="+",
        verbose_name="provozní oprávnění",
    )

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


# --- systémové kódy z číselníků (pravidla licencí, medicalu a rozlétanosti) -------------
# Podklady k předpisům: docs/licence-a-rozletanost.md


class TypLicence(models.TextChoices):
    """Systémové kódy druhů průkazů (číselník ciselniky.DruhPrukazu)."""

    PPL_A = "ppl_a", "PPL(A)"
    LAPL_A = "lapl_a", "LAPL(A)"
    SPL = "spl", "SPL"
    ULL = "ull", "Pilot ULL (LAA ČR)"
    RADIO = "radio", "Radiofonní průkaz (ČTÚ)"
    JAZYK = "jazyk", "Angličtina (ICAO)"


class DruhKvalifikace(models.TextChoices):
    """Systémové kódy kvalifikací (číselník ciselniky.KvalifikacePrukazu)."""

    SEP = "sep", "SEP (land)"
    TMG = "tmg", "TMG"
    NAVIJAK = "navijak", "Naviják / auto"
    VLEK = "vlek", "Aerovlek"
    SAMOSTART = "samostart", "Samostart"
    GUMA = "guma", "Guma (bungee)"
    ULL = "ull", "ULL"
    OFL = "ofl", "Omezený (OFL)"
    VFL = "vfl", "Všeobecný (VFL)"
    EN_4 = "en_4", "ICAO 4"
    EN_5 = "en_5", "ICAO 5"
    EN_6 = "en_6", "ICAO 6"
    VLEKANI = "vlekani", "Vlekání kluzáků"
    FI_S_OMEZENY = "fi_s_omezeny", "FI(S) omezený"


class TridaMedicalu(models.TextChoices):
    """Systémové kódy tříd medicalu (číselník kvalifikací průkazu Medical)."""

    T1 = "t1", "Třída 1"
    T2 = "t2", "Třída 2"
    LAPL = "lapl", "LAPL"


# Které třídy medicalu stačí ke které licenci (radiofonní průkaz medical nepotřebuje).
MEDICAL_LICENCE = {
    TypLicence.PPL_A: [TridaMedicalu.T1, TridaMedicalu.T2],
    TypLicence.LAPL_A: [TridaMedicalu.T1, TridaMedicalu.T2, TridaMedicalu.LAPL],
    TypLicence.SPL: [TridaMedicalu.T1, TridaMedicalu.T2, TridaMedicalu.LAPL],
    TypLicence.ULL: [TridaMedicalu.T1, TridaMedicalu.T2, TridaMedicalu.LAPL],
}


def smi_spravovat_licence(osoba) -> bool:
    """Licence a medical všech pilotů a termíny letadel: správce a admin."""
    return osoba.is_staff or osoba.role_spravce


# --- doklady osoby podle číselníků (etapa 14) -------------------------------------------
# Průkazy, medical, radiofonní průkaz, osvědčení instruktora a pověření examinátora jsou
# všechny „průkaz osoby“ s kvalifikacemi z číselníku (ciselniky.DruhPrukazu a
# KvalifikacePrukazu). Pravidla aplikace pracují se systémovými kódy (TypLicence,
# DruhKvalifikace výše).


class PrukazOsoby(models.Model):
    """Průkaz nebo doklad osoby (pilotní průkaz, medical, osvědčení instruktora…)."""

    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name="prukazy")
    druh = models.ForeignKey(
        "ciselniky.DruhPrukazu", on_delete=models.PROTECT, related_name="+", verbose_name="druh"
    )
    cislo = models.CharField("číslo průkazu", max_length=40, blank=True)
    poznamka = models.CharField("poznámka", max_length=200, blank=True)
    zmeneno = models.DateTimeField("změněno", auto_now=True)

    class Meta:
        verbose_name = "průkaz osoby"
        verbose_name_plural = "průkazy osob"
        constraints = [
            models.UniqueConstraint(fields=["osoba", "druh"], name="prukaz_osoby_jednou"),
        ]

    def __str__(self):
        return f"{self.osoba} – {self.druh}"

    @property
    def typ(self) -> str:
        """Systémový kód druhu (ppl_a, spl, medical…), u vlastních druhů prázdný."""
        return self.druh.kod or ""

    def get_typ_display(self) -> str:
        return self.druh.nazev


class KvalifikaceOsoby(models.Model):
    """Kvalifikace v průkazu osoby (SEP, naviják, třída 2, FI(S)…) a její platnost."""

    prukaz = models.ForeignKey(PrukazOsoby, on_delete=models.CASCADE, related_name="kvalifikace")
    kvalifikace = models.ForeignKey(
        "ciselniky.KvalifikacePrukazu", on_delete=models.PROTECT, related_name="+"
    )
    platnost_do = models.DateField("platnost do", null=True, blank=True)

    class Meta:
        verbose_name = "kvalifikace osoby"
        verbose_name_plural = "kvalifikace osob"
        constraints = [
            models.UniqueConstraint(
                fields=["prukaz", "kvalifikace"], name="kvalifikace_osoby_jednou"
            ),
        ]

    def __str__(self):
        return self.kvalifikace.nazev

    @property
    def druh(self) -> str:
        """Systémový kód kvalifikace (sep, navijak, t2…), u vlastních prázdný."""
        return self.kvalifikace.kod or ""

    def get_druh_display(self) -> str:
        return self.kvalifikace.nazev

    def clean(self):
        if self.prukaz_id and self.kvalifikace.druh_id != self.prukaz.druh_id:
            raise ValidationError("Kvalifikace k tomuto průkazu nepatří.")


class Preskoleni(models.Model):
    """Přeškolení na typ letadla – platí pro všechna letadla toho typu."""

    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name="preskoleni")
    typ = models.ForeignKey(
        "ciselniky.TypLetadla", on_delete=models.PROTECT, related_name="+", verbose_name="typ"
    )
    datum = models.DateField("přeškolen dne", null=True, blank=True)

    class Meta:
        verbose_name = "přeškolení na typ"
        verbose_name_plural = "přeškolení na typy"
        constraints = [models.UniqueConstraint(fields=["osoba", "typ"], name="preskoleni_jednou")]

    def __str__(self):
        return f"{self.osoba} – {self.typ}"


class Vycvik(models.Model):
    """Výcvik žáka na pilotní průkaz (FCL.020: sólo jen s povolením instruktora)."""

    osoba = models.ForeignKey(Osoba, on_delete=models.CASCADE, related_name="vycviky")
    druh = models.ForeignKey(
        "ciselniky.DruhPrukazu",
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="výcvik na",
    )
    zahajen = models.DateField("zahájen", null=True, blank=True)
    solo_povoleno = models.DateField("první sólo povoleno", null=True, blank=True)
    ukoncen = models.DateField("ukončen", null=True, blank=True)
    poznamka = models.CharField("poznámka", max_length=200, blank=True)

    class Meta:
        verbose_name = "výcvik"
        verbose_name_plural = "výcviky"
        ordering = ["-zahajen"]

    def __str__(self):
        return f"{self.osoba} – výcvik {self.druh}"
