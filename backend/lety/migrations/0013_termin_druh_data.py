"""Termíny letadel: název → druh z číselníku (chybějící druhy se do číselníku doplní)."""

from django.db import migrations


def prevest(apps, schema_editor):
    TerminLetadla = apps.get_model("lety", "TerminLetadla")
    DruhTerminu = apps.get_model("ciselniky", "DruhTerminu")
    for termin in TerminLetadla.objects.all():
        termin.druh, _ = DruhTerminu.objects.get_or_create(nazev=termin.nazev.strip())
        termin.save(update_fields=["druh"])


class Migration(migrations.Migration):
    dependencies = [
        ("lety", "0012_termin_druh"),
        ("ciselniky", "0002_vychozi_hodnoty"),
    ]

    operations = [migrations.RunPython(prevest, migrations.RunPython.noop)]
