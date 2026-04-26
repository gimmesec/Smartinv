from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LegalEntity(TimeStampedModel):
    name = models.CharField(max_length=255)
    tax_id = models.CharField(max_length=12, unique=True)
    kpp = models.CharField(max_length=9, blank=True)
    address = models.TextField(blank=True)
    external_1c_id = models.CharField(max_length=128, blank=True, db_index=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.tax_id})"


class Location(TimeStampedModel):
    class LocationType(models.TextChoices):
        OFFICE = "office", "Офис"
        BUILDING = "building", "Здание"
        FLOOR = "floor", "Этаж"
        ROOM = "room", "Помещение"

    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=LocationType.choices)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    external_1c_id = models.CharField(max_length=128, blank=True, db_index=True)

    class Meta:
        unique_together = ("legal_entity", "name", "type", "parent")

    def __str__(self) -> str:
        return f"{self.name} [{self.get_type_display()}]"


class AssetCategory(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class Employee(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="employee_profile",
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, blank=True)
    position = models.CharField(max_length=128, blank=True)
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE, related_name="employees")
    external_1c_id = models.CharField(max_length=128, blank=True, db_index=True)

    def __str__(self) -> str:
        return self.full_name


class Asset(TimeStampedModel):
    class AssetStatus(models.TextChoices):
        ACTIVE = "active", "Исправен"
        DAMAGED = "damaged", "Поврежден"
        LOST = "lost", "Отсутствует"
        WRITTEN_OFF = "written_off", "Списан"

    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.PROTECT, related_name="assets")
    name = models.CharField(max_length=255)
    inventory_number = models.CharField(max_length=128, unique=True)
    serial_number = models.CharField(max_length=128, blank=True)
    category = models.ForeignKey(
        AssetCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="assets"
    )
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name="assets")
    responsible_employee = models.ForeignKey(
        Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name="assets"
    )
    status = models.CharField(max_length=20, choices=AssetStatus.choices, default=AssetStatus.ACTIVE)
    qr_code = models.CharField(max_length=128, blank=True, db_index=True)
    barcode = models.CharField(max_length=128, blank=True, db_index=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    photo = models.ImageField(upload_to="assets/photos/", blank=True, null=True)
    description = models.TextField(blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    last_inventory_at = models.DateTimeField(null=True, blank=True)
    external_1c_id = models.CharField(max_length=128, blank=True, db_index=True)

    def clean(self):
        if not self.responsible_employee and not self.location:
            raise ValidationError("Актив должен быть закреплен за сотрудником или локацией.")

        if self.responsible_employee and self.responsible_employee.legal_entity_id != self.legal_entity_id:
            raise ValidationError("Сотрудник и актив должны принадлежать одному юрлицу.")

        if self.location and self.location.legal_entity_id != self.legal_entity_id:
            raise ValidationError("Локация и актив должны принадлежать одному юрлицу.")

    def __str__(self) -> str:
        return f"{self.inventory_number} - {self.name}"


class InventorySession(TimeStampedModel):
    class SessionStatus(models.TextChoices):
        DRAFT = "draft", "Черновик"
        IN_PROGRESS = "in_progress", "В процессе"
        COMPLETED = "completed", "Завершена"

    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.PROTECT, related_name="inventory_sessions")
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL)
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    conducted_by_employees = models.ManyToManyField("Employee", blank=True, related_name="inventory_sessions")
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.DRAFT)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    external_1c_id = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text="Идентификатор сессии в 1С (GUID/номер документа) для идемпотентного импорта.",
    )

    def __str__(self) -> str:
        return f"Инвентаризация #{self.id}"


class InventoryItem(TimeStampedModel):
    class Condition(models.TextChoices):
        OK = "ok", "Исправен"
        DAMAGED = "damaged", "Поврежден"
        ABSENT = "absent", "Отсутствует"

    session = models.ForeignKey(InventorySession, on_delete=models.CASCADE, related_name="items")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="inventory_items")
    scanned_at = models.DateTimeField(auto_now_add=True)
    detected = models.BooleanField(default=True)
    detected_inventory_number = models.CharField(max_length=128, blank=True)
    ocr_text = models.TextField(blank=True)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.OK)
    ai_condition = models.CharField(max_length=20, choices=Condition.choices, blank=True)
    ai_confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ai_provider = models.CharField(max_length=64, blank=True)
    ai_comment = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    photo = models.ImageField(upload_to="inventory/photos/", blank=True, null=True)

    class Meta:
        unique_together = ("session", "asset")


class Transfer(TimeStampedModel):
    class TransferStatus(models.TextChoices):
        PENDING = "pending", "Ожидает"
        APPROVED = "approved", "Подтвержден"
        REJECTED = "rejected", "Отклонен"

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="transfers")
    from_employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    to_employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    from_location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    to_location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    transfer_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=TransferStatus.choices, default=TransferStatus.PENDING)
    command_text = models.TextField(blank=True)
    external_1c_id = models.CharField(max_length=128, blank=True, db_index=True)


class WriteOffAct(TimeStampedModel):
    class WriteOffStatus(models.TextChoices):
        DRAFT = "draft", "Черновик"
        CONFIRMED = "confirmed", "Подтверждено"
        SENT_TO_1C = "sent_to_1c", "Отправлено в 1С"

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="write_off_acts")
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.PROTECT, related_name="write_off_acts")
    reason = models.TextField()
    wear_level_percent = models.PositiveSmallIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=WriteOffStatus.choices, default=WriteOffStatus.DRAFT)
    external_1c_id = models.CharField(max_length=128, blank=True, db_index=True)

    def clean(self):
        if self.asset_id and self.legal_entity_id and self.asset.legal_entity_id != self.legal_entity_id:
            raise ValidationError("Акт списания и актив должны принадлежать одному юрлицу.")


class OneCExchangeLog(TimeStampedModel):
    class Direction(models.TextChoices):
        IMPORT = "import", "Импорт из 1С"
        EXPORT = "export", "Экспорт в 1С"

    class Status(models.TextChoices):
        SUCCESS = "success", "Успешно"
        ERROR = "error", "Ошибка"

    direction = models.CharField(max_length=10, choices=Direction.choices)
    status = models.CharField(max_length=10, choices=Status.choices)
    payload = models.TextField(blank=True)
    response = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
