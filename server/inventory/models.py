# inventory/models.py
from django.db import models
from django.utils import timezone
from users.models import User, Object
from tools.models import Tool

# -----------------------
# Инвентаризация
# -----------------------
class InventoryCheck(models.Model):
    """
    Инвентаризация инструментов на объекте.
    """
    date = models.DateTimeField(default=timezone.now)
    object = models.ForeignKey(Object, on_delete=models.PROTECT, related_name='inventory_checks')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='inventory_checks')
    tools = models.ManyToManyField(Tool, through='ToolOnCheck', related_name='inventory_checks')

    def __str__(self):
        return f"Инвентаризация на {self.object.name} ({self.date.strftime('%Y-%m-%d %H:%M')})"


# -----------------------
# Промежуточная таблица между инвентаризацией и инструментом
# -----------------------
class ToolOnCheck(models.Model):
    """
    Промежуточная модель для связи инструментов с конкретной инвентаризацией.
    """
    inventory_check = models.ForeignKey(InventoryCheck, on_delete=models.CASCADE)
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('inventory_check', 'tool')

    def __str__(self):
        return f"{self.tool} на {self.inventory_check}"
