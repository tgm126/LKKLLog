from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("lety", "0013_termin_druh_data")]

    operations = [
        migrations.RemoveField(model_name="terminletadla", name="nazev"),
        migrations.AlterField(
            model_name="terminletadla",
            name="druh",
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name="+",
                to="ciselniky.druhterminu",
                verbose_name="druh",
            ),
        ),
        migrations.AlterModelOptions(
            name="terminletadla",
            options={
                "ordering": ["letadlo", "datum", "pri_naletu_h"],
                "verbose_name": "termín letadla",
                "verbose_name_plural": "termíny letadel",
            },
        ),
    ]
