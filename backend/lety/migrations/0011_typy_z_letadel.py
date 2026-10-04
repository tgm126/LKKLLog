"""Číselník typů letadel z dosavadních letadel; letadla se na svůj typ odkážou."""

from django.db import migrations


def typy(apps, schema_editor):
    Letadlo = apps.get_model("lety", "Letadlo")
    TypLetadla = apps.get_model("ciselniky", "TypLetadla")
    for letadlo in Letadlo.objects.all().order_by("poradi", "imatrikulace"):
        nazev = letadlo.typ.strip() or letadlo.imatrikulace
        typ = TypLetadla.objects.filter(nazev=nazev).first()
        if typ and typ.kategorie != letadlo.kategorie:  # stejný název v jiné kategorii
            nazev = f"{nazev} ({letadlo.kategorie})"
            typ = TypLetadla.objects.filter(nazev=nazev).first()
        if typ is None:
            typ = TypLetadla.objects.create(nazev=nazev, kategorie=letadlo.kategorie)
        letadlo.typ_letadla = typ
        letadlo.save(update_fields=["typ_letadla"])


class Migration(migrations.Migration):
    dependencies = [
        ("lety", "0010_typ_letadla"),
        ("ciselniky", "0002_vychozi_hodnoty"),
    ]

    operations = [migrations.RunPython(typy, migrations.RunPython.noop)]
