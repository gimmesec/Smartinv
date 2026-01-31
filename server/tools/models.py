from django.db import models
from users.models import Object  # подключаем модель Object
from django.utils import timezone

# -----------------------
# Названия инструментов
# -----------------------
class ToolName(models.Model):
    """
    Тип или название инструмента.
    Примеры: Отвёртка, Перфоратор, Шуруповёрт.
    """
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


# -----------------------
# Статусы инструментов
# -----------------------
class Status(models.Model):
    """
    Статус инструмента.
    Примеры: Новый, Рабочий, Сломан, Списан.
    """
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# -----------------------
# Основная модель инструмента
# -----------------------
class Tool(models.Model):
    """
    Инструмент, принадлежащий системе учёта.
    """
    inventory_number = models.CharField(max_length=255, unique=True)
    tool_name = models.ForeignKey(ToolName, on_delete=models.PROTECT, related_name='tools')
    qr_code_value = models.CharField(max_length=255, unique=True)
    current_object = models.ForeignKey(Object, on_delete=models.SET_NULL, null=True, blank=True, related_name='tools')
    status = models.ForeignKey(Status, on_delete=models.PROTECT, related_name='tools')
    photo = models.ImageField(upload_to='tools/', null=True, blank=True)
    
    # Дополнительная служебная информация
    description = models.TextField(blank=True)  # можно описывать назначение или особенности инструмента
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tool_name.name} ({self.inventory_number})"


# -----------------------
# Списание инструмента
# -----------------------
class WrittenOffTool(models.Model):
    """
    История списания сломанных инструментов.
    """
    tool = models.OneToOneField(Tool, on_delete=models.CASCADE, related_name='written_off')
    broken_photo = models.ImageField(upload_to='written_off_tools/')  # фото сломанного инструмента
    qr_photo = models.ImageField(upload_to='written_off_tools/qr/')   # фото QR-кода (если нужен скан)
    description = models.TextField(help_text="Описание как и почему инструмент сломался")
    date = models.DateTimeField(default=timezone.now)
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='reported_written_off_tools')

    def __str__(self):
        return f"{self.tool} - списан ({self.date.strftime('%Y-%m-%d')})"
