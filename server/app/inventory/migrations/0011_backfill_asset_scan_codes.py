from django.db import migrations


def backfill_asset_scan_codes(apps, schema_editor):
    Asset = apps.get_model("inventory", "Asset")
    for asset in Asset.objects.all().only("id", "inventory_number", "qr_code", "barcode"):
        code = (asset.inventory_number or "").strip()
        if not code:
            continue
        updates = []
        if not (asset.qr_code or "").strip():
            asset.qr_code = code
            updates.append("qr_code")
        if not (asset.barcode or "").strip():
            asset.barcode = code
            updates.append("barcode")
        if updates:
            asset.save(update_fields=updates)


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0010_assetconditionjob_source_images"),
    ]

    operations = [
        migrations.RunPython(backfill_asset_scan_codes, migrations.RunPython.noop),
    ]
