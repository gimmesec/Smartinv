from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0003_inventorysession_conducted_by_employees"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="quantity",
            field=models.DecimalField(decimal_places=2, default=1, max_digits=12),
        ),
        migrations.AddField(
            model_name="asset",
            name="unit_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
    ]
