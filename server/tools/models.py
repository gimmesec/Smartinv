from django.db import models
from common.models import AuditMixin


class ToolStatus(models.TextChoices):
    """Статусы инструмента."""
    IN_STOCK = 'in_stock', 'В наличии'
    IN_WORK = 'in_work', 'В работе'
    TRANSFERRED = 'transferred', 'Передан'
    WRITTEN_OFF = 'written_off', 'Списан'


class ToolName(models.Model):
    """Справочник названий инструментов."""
    name = models.CharField(max_length=255, unique=True, verbose_name='Название')

    class Meta:
        verbose_name = 'Название инструмента'
        verbose_name_plural = 'Названия инструментов'
        ordering = ['name']

    def __str__(self):
        return self.name


class Tool(AuditMixin):
    """Инструмент."""
    tool_name = models.ForeignKey(
        ToolName,
        on_delete=models.PROTECT,
        related_name='tools',
        verbose_name='Название'
    )
    inventory_number = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Инвентарный номер'
    )
    qr_code = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='QR-код'
    )
    photo = models.ImageField(
        upload_to='tools/',
        null=True,
        blank=True,
        verbose_name='Фото инструмента'
    )
    current_object = models.ForeignKey(
        'objects.ConstructionObject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tools',
        verbose_name='Текущий объект'
    )
    status = models.CharField(
        max_length=20,
        choices=ToolStatus.choices,
        default=ToolStatus.IN_STOCK,
        verbose_name='Статус'
    )

    class Meta:
        verbose_name = 'Инструмент'
        verbose_name_plural = 'Инструменты'
        ordering = ['inventory_number']

    def __str__(self):
        return f"{self.tool_name.name} ({self.inventory_number})"


class ToolTransferHistory(AuditMixin):
    """История перемещений инструмента между объектами."""
    tool = models.ForeignKey(
        Tool,
        on_delete=models.CASCADE,
        related_name='transfer_history',
        verbose_name='Инструмент'
    )
    from_object = models.ForeignKey(
        'objects.ConstructionObject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tool_transfers_from',
        verbose_name='Объект-отправитель'
    )
    to_object = models.ForeignKey(
        'objects.ConstructionObject',
        on_delete=models.PROTECT,
        related_name='tool_transfers_to',
        verbose_name='Объект-получатель'
    )
    transfer_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата перемещения')

    class Meta:
        verbose_name = 'История перемещения инструмента'
        verbose_name_plural = 'История перемещений инструментов'
        ordering = ['-transfer_date']

    def __str__(self):
        return f"{self.tool} -> {self.to_object} ({self.transfer_date.strftime('%Y-%m-%d')})"
