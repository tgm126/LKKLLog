from fnmatch import fnmatch

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

    def smi_odeslat(self, adresa: str) -> bool:
        if self.email_rezim == EmailRezim.VSE:
            return True
        if self.email_rezim == EmailRezim.POVOLENE:
            adresa = adresa.strip().lower()
            vzory = [r.strip().lower() for r in self.povolene_adresy.splitlines() if r.strip()]
            return any(fnmatch(adresa, vzor) for vzor in vzory)
        return False
