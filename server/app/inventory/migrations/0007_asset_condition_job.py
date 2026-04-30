import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0006_asset_photo_history"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssetConditionJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "В очереди"),
                            ("vision_running", "Анализ изображения"),
                            ("vision_done", "Изображение обработано"),
                            ("llm_running", "Генерация текста"),
                            ("completed", "Готово"),
                            ("failed", "Ошибка"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=32,
                    ),
                ),
                ("vision_result", models.JSONField(blank=True, default=dict)),
                ("llm_summary", models.TextField(blank=True)),
                ("error_message", models.TextField(blank=True)),
                (
                    "source_image",
                    models.CharField(
                        blank=True,
                        help_text="Относительный путь файла внутри MEDIA_ROOT (например assets/photos/x.jpg).",
                        max_length=512,
                    ),
                ),
                (
                    "asset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="condition_jobs",
                        to="inventory.asset",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
    ]
