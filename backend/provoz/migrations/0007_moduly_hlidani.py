"""Jeden přepínač hlídání → tři moduly (způsobilost, rozlétanost, letadla).

Dosavadní hodnota „hlídat licence, medical a rozlétanost“ se přenese do obou modulů
pilotů; hlídání letadel začíná vypnuté.
"""

from django.db import migrations, models


def prenest(apps, schema_editor):
    Nastaveni = apps.get_model("provoz", "Nastaveni")
    for n in Nastaveni.objects.all():
        n.hlidat_rozletanost = n.hlidat_zpusobilost
        n.save(update_fields=["hlidat_rozletanost"])


class Migration(migrations.Migration):
    dependencies = [
        ("provoz", "0006_hlidat_licence"),
    ]

    operations = [
        migrations.RenameField("nastaveni", "hlidat_licence", "hlidat_zpusobilost"),
        migrations.AlterField(
            model_name="nastaveni",
            name="hlidat_zpusobilost",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Licence, kvalifikace, medical, radiofonní průkaz a jazyková způsobilost: "
                    "varování při zakládání letu a přehled v Můj nálet."
                ),
                verbose_name="hlídat způsobilost pilotů",
            ),
        ),
        migrations.AddField(
            model_name="nastaveni",
            name="hlidat_rozletanost",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Nálet a starty za období, cestující (90 dní): varování a přehled v Můj nálet."
                ),
                verbose_name="hlídat rozlétanost pilotů",
            ),
        ),
        migrations.AddField(
            model_name="nastaveni",
            name="hlidat_letadla",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Varování při zakládání letu, když má letadlo prošlý termín "
                    "(ARC, prohlídka…)."
                ),
                verbose_name="hlídat způsobilost letadel",
            ),
        ),
        migrations.RunPython(prenest, migrations.RunPython.noop),
    ]
