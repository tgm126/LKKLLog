import secrets
from fnmatch import fnmatch

from django.conf import settings
from django.db import models


class EmailRezim(models.TextChoices):
    VYPNUTO = "vypnuto", "Vypnuto – nic se neodesílá"
    POVOLENE = "povolene", "Jen povolené adresy"
    VSE = "vse", "Všem"


class Nastaveni(models.Model):
    """Nastavení provozu aplikace. Existuje jen jeden záznam (Nastaveni.aktualni())."""

    email_rezim = models.CharField(
        "režim odesílání e-mailů",
        max_length=10,
        choices=EmailRezim.choices,
        default=EmailRezim.VYPNUTO,
        help_text="Do spuštění pro celý klub nechte „Jen povolené adresy“ nebo „Vypnuto“.",
    )
    povolene_adresy = models.TextField(
        "povolené adresy",
        blank=True,
        help_text=(
            "Jedna adresa na řádek. Lze použít hvězdičku, např. tomas.mandlik+*@gmail.com "
            "povolí všechny adresy s přídavkem."
        ),
    )
    testovaci_provoz = models.BooleanField(
        "testovací provoz",
        default=True,
        help_text="V záhlaví aplikace se zobrazí pruh „TESTOVACÍ PROVOZ“.",
    )

    automaticka_uzaverka = models.BooleanField(
        "automatická denní uzávěrka",
        default=True,
        help_text=(
            "Každý den v 5:00 se uzavře předchozí den, pokud v něm nic neletí ani není "
            "připravené. Piloti pak už do dne nic nedopíší – zapíše to časoměřič nebo účetní."
        ),
    )

    # Moduly hlídání – zapínají se, až jsou data kompletní. Varování nic neblokují.
    hlidat_zpusobilost = models.BooleanField(
        "hlídat způsobilost pilotů",
        default=False,
        help_text=(
            "Licence, kvalifikace, medical a radiofonní průkaz: "
            "varování při zakládání letu a přehled v Můj nálet."
        ),
    )
    hlidat_rozletanost = models.BooleanField(
        "hlídat rozlétanost pilotů",
        default=False,
        help_text="Nálet a starty za období, cestující (90 dní): varování a přehled v Můj nálet.",
    )
    hlidat_letadla = models.BooleanField(
        "hlídat způsobilost letadel",
        default=False,
        help_text="Varování při zakládání letu, když má letadlo prošlý termín (ARC, prohlídka…).",
    )
    displej_klic = models.CharField(
        "klíč velkého displeje",
        max_length=64,
        blank=True,
        help_text="Tajná část odkazu na displej bez přihlášení. Prázdné = displej vypnutý.",
    )

    class Meta:
        verbose_name = "nastavení"
        verbose_name_plural = "nastavení"

    def __str__(self):
        return "Nastavení aplikace"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def aktualni(cls) -> Nastaveni:
        nastaveni, _ = cls.objects.get_or_create(pk=1)
        return nastaveni

    def novy_klic_displeje(self) -> str:
        """Nový odkaz na displej; starý tím přestane platit.

        Jen šestnáctkové znaky – v náhodném textu tak nemůže vzniknout slovo, které
        nginx VPS Centra v adresách blokuje (log, bin, tmp…).
        """
        self.displej_klic = secrets.token_hex(16)
        return self.displej_klic

    @property
    def odkaz_displeje(self) -> str:
        return f"{settings.APP_URL}/displej/{self.displej_klic}" if self.displej_klic else ""

    def smi_odeslat(self, adresa: str) -> bool:
        if self.email_rezim == EmailRezim.VSE:
            return True
        if self.email_rezim == EmailRezim.POVOLENE:
            adresa = adresa.strip().lower()
            vzory = [r.strip().lower() for r in self.povolene_adresy.splitlines() if r.strip()]
            return any(fnmatch(adresa, vzor) for vzor in vzory)
        return False


class PushOdber(models.Model):
    """Zařízení (prohlížeč), na které osoba chce dostávat upozornění (Web Push)."""

    osoba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_odbery"
    )
    endpoint = models.URLField("adresa push služby", max_length=1000, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    zarizeni = models.CharField("zařízení", max_length=200, blank=True)
    vytvoreno = models.DateTimeField("zapnuto", auto_now_add=True)

    class Meta:
        verbose_name = "zařízení pro upozornění"
        verbose_name_plural = "zařízení pro upozornění"

    def __str__(self):
        return f"{self.osoba} – {self.zarizeni or 'zařízení'}"
