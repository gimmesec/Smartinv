from django.db import models
from django.utils import timezone
from common.models import AuditMixin


class Inventory(AuditMixin):
    """Инвентаризация инструментов на объекте."""
    date = models.DateTimeField(default=timezone.now, verbose_name='Дата и время')
    object = models.ForeignKey(
        'objects.ConstructionObject',
        on_delete=models.PROTECT,
        related_name='inventories',
        verbose_name='Объект'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='inventories',
        verbose_name='Пользователь, проводивший инвентаризацию'
    )
    tools = models.ManyToManyField(
        'tools.Tool',
        through='InventoryTool',
        related_name='inventories',
        verbose_name='Инструменты'
    )

    class Meta:
        verbose_name = 'Инвентаризация'
        verbose_name_plural = 'Инвентаризации'
        ordering = ['-date']

    def __str__(self):
        return f"Инвентаризация на {self.object.name} ({self.date.strftime('%Y-%m-%d %H:%M')})"


class InventoryTool(models.Model):
    """Промежуточная модель для связи инструментов с инвентаризацией."""
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name='inventory_tools'
    )
    tool = models.ForeignKey(
        'tools.Tool',
        on_delete=models.CASCADE,
        related_name='inventory_tools'
    )
    is_present = models.BooleanField(
        default=True,
        verbose_name='Присутствует'
    )

    class Meta:
        unique_together = ('inventory', 'tool')
        verbose_name = 'Инструмент в инвентаризации'
        verbose_name_plural = 'Инструменты в инвентаризациях'

    def __str__(self):
        status = "присутствует" if self.is_present else "отсутствует"
        return f"{self.tool} - {status}"
