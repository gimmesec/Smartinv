from django.db import migrations, models


def copy_source_image_to_list(apps, schema_editor):
    Job = apps.get_model("inventory", "AssetConditionJob")
    for job in Job.objects.exclude(source_image=""):
        if job.source_images:
            continue
        job.source_images = [job.source_image]
        job.save(update_fields=["source_images"])


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0009_assetphoto_session_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="assetconditionjob",
            name="source_images",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(copy_source_image_to_list, migrations.RunPython.noop),
    ]
