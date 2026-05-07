from django.db import migrations, models
import django.db.models.deletion


def copy_asset_photos_to_history(apps, schema_editor):
    Asset = apps.get_model("inventory", "Asset")
    AssetPhoto = apps.get_model("inventory", "AssetPhoto")
    for asset in Asset.objects.exclude(photo="").exclude(photo__isnull=True):
        if AssetPhoto.objects.filter(asset_id=asset.id, photo=asset.photo).exists():
            continue
        AssetPhoto.objects.create(asset_id=asset.id, photo=asset.photo)


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0008_flat_location"),
    ]

    operations = [
        migrations.AlterField(
            model_name="assetphoto",
            name="session",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="asset_photos",
                to="inventory.inventorysession",
            ),
        ),
        migrations.RunPython(copy_asset_photos_to_history, migrations.RunPython.noop),
    ]
