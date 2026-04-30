from django.db import migrations
from django.db.models import Count


def _flatten_location_names(apps, schema_editor):
    Location = apps.get_model("inventory", "Location")
    for loc in Location.objects.all().order_by("id"):
        names = []
        cur = loc
        seen_ids = set()
        for _ in range(100):
            if cur is None or cur.id in seen_ids:
                break
            seen_ids.add(cur.id)
            names.insert(0, cur.name)
            pid = getattr(cur, "parent_id", None)
            if not pid:
                break
            cur = Location.objects.filter(pk=pid).first()
        full = " — ".join(names)
        if len(full) > 255:
            full = full[:252] + "..."
        Location.objects.filter(pk=loc.pk).update(name=full)

    dup_groups = (
        Location.objects.values("legal_entity_id", "name")
        .annotate(c=Count("id"))
        .filter(c__gt=1)
    )
    for row in dup_groups:
        pks = list(
            Location.objects.filter(legal_entity_id=row["legal_entity_id"], name=row["name"])
            .order_by("id")
            .values_list("id", flat=True)
        )
        for dup_id in pks[1:]:
            suffix = f" #{dup_id}"
            loc = Location.objects.get(pk=dup_id)
            new_name = (loc.name[: 255 - len(suffix)] + suffix)[:255]
            Location.objects.filter(pk=dup_id).update(name=new_name)


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0007_asset_condition_job"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="location",
            unique_together=set(),
        ),
        migrations.RunPython(_flatten_location_names, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="location",
            name="parent",
        ),
        migrations.RemoveField(
            model_name="location",
            name="type",
        ),
        migrations.AlterUniqueTogether(
            name="location",
            unique_together={("legal_entity", "name")},
        ),
    ]
