from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0002_employee_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventorysession",
            name="conducted_by_employees",
            field=models.ManyToManyField(blank=True, related_name="inventory_sessions", to="inventory.employee"),
        ),
    ]
