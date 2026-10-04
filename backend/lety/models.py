from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import ArrayField, DateTimeRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Func, Q

from osoby.models import Kategorie


class Ucel(models.TextChoices):
    """Účel letu. Spolu s kategorií letadla tvoří typ letu (kap. 3.1 návrhu)."""

    NORMALNI = "normalni", "Normální"
    VYCVIK = "vycvik", "Výcvik"
    VYCVIK_SOLO = "vycvik_solo", "Výcvik sólo"
    PREZKOUSENI = "prezkouseni", "Přezkoušení"
    VLEK = "vlek", "Vlek"


class ZpusobVzletu(models.TextChoices):
    VLASTNI = "vlastni", "Vlastní"
    NAVIJAK = "navijak", "Naviják"
    VLEK = "vlek", "Vlek"
    AUTOSTART = "autostart", "Autostart"


class StavLetu(models.TextChoices):
    PRIPRAVEN = "pripraven", "Připraven"
    VE_VZDUCHU = "ve_vzduchu", "Ve vzduchu"
    UKONCEN = "ukoncen", "Ukončen"
    ZRUSEN = "zrusen", "Zrušen"


class DuvodZruseni(models.TextChoices):
    TECHNICKA_ZAVADA = "technicka_zavada", "Technická závada"
    POCASI = "pocasi", "Počasí"
    OMYL = "omyl", "Založeno omylem"
    PRERUSENY_VZLET = "preruseny_vzlet", "Přerušený vzlet"
    JINE = "jine", "Jiné"


class KratkyLet(models.TextChoices):
    """Volba u letu do 1 minuty (kap. 3.5 návrhu)."""

    START_BEZ_DOBY = "start_bez_doby", "Start se počítá, doba 0 min"
    NORMALNI = "normalni", "Normální let"


class FunkcePosadky(models.TextChoices):
    PIC = "pic", "PIC"
    ZAK = "zak", "Žák"
    PREZKOUSENY = "prezkouseny", "Přezkoušený"
    DOZOR = "dozor", "Dozor (na zemi)"
    CLEN = "clen", "Člen posádky"


class Letadlo(models.Model):
    imatrikulace = models.CharField(max_length=10, unique=True, help_text="např. OK-0815")
    typ = models.CharField(max_length=60, help_text="např. L-13 Blaník")
    kategorie = models.CharField(max_length=10, choices=Kategorie.choices)
    pocet_mist = models.PositiveSmallIntegerField("počet míst", default=2)
    max_doba_min = models.PositiveIntegerField(
        "max. doba letu [min]",
        null=True,
        blank=True,
        help_text="S plnými nádržemi. U kluzáků prázdné.",
    )
    soukrome = models.BooleanField(
        "soukromé", default=False, help_text="Neexportuje se pro účetnictví."
    )
    vlecne = models.BooleanField("vlečné", default=False, help_text="Může vlekat kluzáky.")
    aktivni = models.BooleanField("aktivní", default=True)
    poradi = models.PositiveSmallIntegerField("pořadí", default=100)

    class Meta:
        verbose_name = "letadlo"
        verbose_name_plural = "letadla"
        ordering = ["poradi", "imatrikulace"]
        constraints = [
            models.CheckConstraint(
                condition=Q(pocet_mist__gte=1, pocet_mist__lte=4), name="letadlo_pocet_mist"
            ),
            models.CheckConstraint(
                condition=~Q(kategorie=Kategorie.KLUZAK)
                | Q(vlecne=False, max_doba_min__isnull=True),
                name="kluzak_bez_vleku_a_nadrzi",
                violation_error_message=(
                    "Kluzák nemůže být vlečný ani mít maximální dobu letu (nemá nádrže)."
                ),
            ),
        ]

    def __str__(self):
        return f"{self.imatrikulace} ({self.typ})"


class Letiste(models.Model):
    icao = models.CharField("ICAO", max_length=4, unique=True, null=True, blank=True)
    nazev = models.CharField("název", max_length=80)
    domovske = models.BooleanField("domovské", default=False)
    teren = models.BooleanField(
        "mimo letiště", default=False, help_text="Přistání do terénu (bez ICAO kódu)."
    )
    aktivni = models.BooleanField("aktivní", default=True)
    poradi = models.PositiveSmallIntegerField("pořadí", default=100)

    class Meta:
        verbose_name = "letiště"
        verbose_name_plural = "letiště"
        ordering = ["-domovske", "poradi", "nazev"]
        constraints = [
            models.UniqueConstraint(
                fields=["domovske"], condition=Q(domovske=True), name="jedno_domovske_letiste"
            ),
        ]

    def __str__(self):
        return f"{self.icao} {self.nazev}" if self.icao else self.nazev


class Uloha(models.Model):
    kod = models.CharField("kód", max_length=20)
    nazev = models.CharField("název", max_length=120)
    osnova = models.CharField(max_length=60, blank=True, help_text="Ke které osnově patří.")
    ucely = ArrayField(
        models.CharField(max_length=12, choices=Ucel.choices),
        verbose_name="účely",
        help_text="Pro které účely letu se úloha nabízí.",
    )
    kategorie = ArrayField(
        models.CharField(max_length=10, choices=Kategorie.choices),
        help_text="Pro které kategorie letadel se úloha nabízí.",
    )
    aktivni = models.BooleanField("aktivní", default=True)
    poradi = models.PositiveSmallIntegerField("pořadí", default=100)

    class Meta:
        verbose_name = "úloha"
        verbose_name_plural = "úlohy"
        ordering = ["poradi", "kod"]
        constraints = [
            models.UniqueConstraint(fields=["osnova", "kod"], name="uloha_unikatni_kod"),
        ]

    def __str__(self):
        return f"{self.kod} – {self.nazev}"


class DobaLetuMin(Func):
    """Doba letu v celých minutách: (přistání − vzlet) zaokrouhleno, 30 s a víc nahoru.

    Počítá ji přímo databáze, takže je všude stejná. Pozor: Pythonové `round()`
    zaokrouhluje 20,5 na 20 (bankovní zaokrouhlení), proto se nepoužívá.
    """

    template = "(FLOOR((EXTRACT(EPOCH FROM (%(expressions)s)) + 30) / 60))::integer"
    output_field = models.IntegerField()


class TstzRange(Func):
    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class Let(models.Model):
    stav = models.CharField(max_length=12, choices=StavLetu.choices, default=StavLetu.PRIPRAVEN)
    letadlo = models.ForeignKey(Letadlo, on_delete=models.PROTECT, related_name="lety")
    ucel = models.CharField("účel", max_length=12, choices=Ucel.choices)
    uloha = models.ForeignKey(
        Uloha,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="lety",
        verbose_name="úloha",
    )
    zpusob_vzletu = models.CharField(
        "způsob vzletu",
        max_length=10,
        choices=ZpusobVzletu.choices,
        default=ZpusobVzletu.VLASTNI,
    )
    vlecny_let = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vleceny_let",
        verbose_name="let vlečného letadla",
        help_text="Jen u kluzáku ve vleku.",
    )

    misto_vzletu = models.ForeignKey(
        Letiste, on_delete=models.PROTECT, related_name="+", verbose_name="místo vzletu"
    )
    misto_pristani = models.ForeignKey(
        Letiste,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="místo přistání",
    )
    cas_vzletu = models.DateTimeField("vzlet (UTC)", null=True, blank=True)
    cas_pristani = models.DateTimeField("přistání (UTC)", null=True, blank=True)
    doba_min = models.GeneratedField(
        expression=DobaLetuMin(F("cas_pristani") - F("cas_vzletu")),
        output_field=models.IntegerField(),
        db_persist=True,
        verbose_name="doba [min]",
    )
    kratky_let = models.CharField(
        "krátký let",
        max_length=16,
        choices=KratkyLet.choices,
        blank=True,
        help_text="Jen u letů do 1 minuty.",
    )
    pocet_tg = models.PositiveSmallIntegerField("touch-and-go", default=0)
    pocet_hostu = models.PositiveSmallIntegerField(
        "hosté", default=0, help_text="Osoby mimo klub (jen počet)."
    )

    platce = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="placene_lety",
        verbose_name="plátce",
    )
    plati_aeroklub = models.BooleanField("platí aeroklub", default=False)
    soukrome = models.BooleanField(
        "soukromé letadlo",
        default=False,
        help_text="Kopie příznaku letadla v okamžiku letu.",
    )

    duvod_zruseni = models.CharField(
        "důvod zrušení", max_length=20, choices=DuvodZruseni.choices, blank=True
    )
    opraveno_po_uzaverce = models.BooleanField("opraveno po uzávěrce", default=False)

    zalozil = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="zalozene_lety",
        verbose_name="založil",
    )
    zalozeno = models.DateTimeField("založeno", auto_now_add=True)
    zmeneno = models.DateTimeField("změněno", auto_now=True)
    verze = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "let"
        verbose_name_plural = "lety"
        ordering = ["-cas_vzletu", "-id"]
        indexes = [models.Index(fields=["cas_vzletu"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(cas_pristani__isnull=True)
                | Q(cas_vzletu__isnull=False, cas_pristani__gte=F("cas_vzletu")),
                name="pristani_po_vzletu",
                violation_error_message="Přistání nemůže být dřív než vzlet.",
            ),
            models.CheckConstraint(
                condition=Q(plati_aeroklub=True, platce__isnull=True)
                | Q(plati_aeroklub=False, platce__isnull=False),
                name="prave_jeden_platce",
                violation_error_message="Let platí buď jedna osoba, nebo aeroklub.",
            ),
            models.CheckConstraint(
                condition=Q(stav=StavLetu.ZRUSEN) | Q(duvod_zruseni=""),
                name="duvod_jen_u_zruseneho",
            ),
            models.CheckConstraint(
                condition=~Q(stav=StavLetu.ZRUSEN) | ~Q(duvod_zruseni=""),
                name="zruseny_ma_duvod",
                violation_error_message="Zrušený let musí mít důvod.",
            ),
            # Jedno letadlo nemůže mít dva časově překrývající se lety.
            # Let bez přistání (ve vzduchu) se bere jako „do nekonečna“.
            ExclusionConstraint(
                name="letadlo_bez_prekryvu",
                expressions=[
                    ("letadlo", RangeOperators.EQUAL),
                    (TstzRange("cas_vzletu", "cas_pristani"), RangeOperators.OVERLAPS),
                ],
                condition=Q(cas_vzletu__isnull=False) & ~Q(stav=StavLetu.ZRUSEN),
                violation_error_message="Letadlo už má v tomto čase jiný let.",
            ),
        ]

    def __str__(self):
        cas = self.cas_vzletu.strftime("%d.%m.%Y %H:%M") if self.cas_vzletu else "připraven"
        return f"{self.letadlo.imatrikulace} {cas}"

    @property
    def doba_uctovana_min(self) -> int | None:
        """Doba, která se počítá do součtů (zrušené lety a „start bez doby“ = 0)."""
        if self.stav == StavLetu.ZRUSEN or self.kratky_let == KratkyLet.START_BEZ_DOBY:
            return 0
        return self.doba_min

    def clean(self):
        if self.vlecny_let_id and self.zpusob_vzletu != ZpusobVzletu.VLEK:
            raise ValidationError("Vlečný let lze přiřadit jen kluzáku se vzletem „vlek“.")


class Posadka(models.Model):
    let = models.ForeignKey(Let, on_delete=models.CASCADE, related_name="posadka")
    osoba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="posadky"
    )
    funkce = models.CharField(max_length=12, choices=FunkcePosadky.choices)

    class Meta:
        verbose_name = "člen posádky"
        verbose_name_plural = "posádka"
        constraints = [
            models.UniqueConstraint(fields=["let", "osoba"], name="osoba_jednou_na_letu"),
            models.UniqueConstraint(
                fields=["let"], condition=Q(funkce=FunkcePosadky.PIC), name="jeden_pic_na_letu"
            ),
        ]

    def __str__(self):
        return f"{self.osoba} ({self.get_funkce_display()})"


class AuditLog(models.Model):
    """Historie změn. Do tabulky se jen zapisuje – úpravy a mazání blokuje databáze."""

    kdy = models.DateTimeField(auto_now_add=True, db_index=True)
    kdo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    akce = models.CharField(max_length=30)
    objekt = models.CharField(max_length=30)
    objekt_id = models.BigIntegerField()
    zmeny = models.JSONField(default=dict, blank=True)
    duvod = models.CharField("důvod", max_length=30, blank=True)
    poznamka = models.CharField("poznámka", max_length=300, blank=True)

    class Meta:
        verbose_name = "záznam auditního logu"
        verbose_name_plural = "auditní log"
        ordering = ["-kdy", "-id"]
        indexes = [models.Index(fields=["objekt", "objekt_id"])]

    def __str__(self):
        return f"{self.kdy:%d.%m.%Y %H:%M} {self.akce} {self.objekt} {self.objekt_id}"


class Uzaverka(models.Model):
    """Uložený souhrn za den nebo měsíc. Není to zámek – opravy po ní jsou možné."""

    class Typ(models.TextChoices):
        DEN = "den", "Den"
        MESIC = "mesic", "Měsíc"

    typ = models.CharField(max_length=5, choices=Typ.choices)
    obdobi = models.DateField("období", help_text="Datum dne, nebo první den měsíce.")
    verze = models.PositiveSmallIntegerField(default=1)
    uzavrel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="uzavřel",
    )
    kdy = models.DateTimeField(auto_now_add=True)
    souhrn = models.JSONField(default=dict)

    class Meta:
        verbose_name = "uzávěrka"
        verbose_name_plural = "uzávěrky"
        ordering = ["-obdobi", "-verze"]
        constraints = [
            models.UniqueConstraint(fields=["typ", "obdobi", "verze"], name="uzaverka_verze"),
        ]

    def __str__(self):
        return f"{self.get_typ_display()} {self.obdobi} v{self.verze}"
