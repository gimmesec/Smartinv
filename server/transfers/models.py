from django.db import models
from django.utils import timezone
from common.models import AuditMixin


class TransferStatus(models.TextChoices):
    """Статусы передачи инструмента."""
    CREATED = 'created', 'Создан'
    CONFIRMED = 'confirmed', 'Подтверждён'
    REJECTED = 'rejected', 'Отклонён'
    COMPLETED = 'completed', 'Выполнен'


class Transfer(AuditMixin):
    """Передача инструмента между объектами."""
    tool = models.ForeignKey(
        'tools.Tool',
        on_delete=models.PROTECT,
        related_name='transfers',
        verbose_name='Инструмент'
    )
    from_object = models.ForeignKey(
        'objects.ConstructionObject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_from',
        verbose_name='Объект-отправитель'
    )
    to_object = models.ForeignKey(
        'objects.ConstructionObject',
        on_delete=models.PROTECT,
        related_name='transfers_to',
        verbose_name='Объект-получатель'
    )
    foreman = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='initiated_transfers',
        verbose_name='Бригадир, инициировавший запрос',
        limit_choices_to={'role': 'foreman'}
    )
    status = models.CharField(
        max_length=20,
        choices=TransferStatus.choices,
        default=TransferStatus.CREATED,
        verbose_name='Статус'
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Дата создания')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата выполнения')

    class Meta:
        verbose_name = 'Передача инструмента'
        verbose_name_plural = 'Передачи инструментов'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tool} -> {self.to_object} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        """Автоматически устанавливаем дату выполнения при завершении передачи."""
        if self.status == TransferStatus.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)
