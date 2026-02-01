from django.db import models
from django.utils import timezone
from common.models import AuditMixin


class WriteOff(AuditMixin):
    """Списание инструмента."""
    tool = models.OneToOneField(
        'tools.Tool',
        on_delete=models.CASCADE,
        related_name='writeoff',
        verbose_name='Инструмент'
    )
    broken_photo = models.ImageField(
        upload_to='writeoff/broken/',
        verbose_name='Фото сломанного инструмента'
    )
    qr_photo = models.ImageField(
        upload_to='writeoff/qr/',
        verbose_name='Фото QR-кода'
    )
    description = models.TextField(verbose_name='Описание причины списания')
    user = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='writeoffs',
        verbose_name='Пользователь, оформивший списание'
    )
    writeoff_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата и время списания'
    )

    class Meta:
        verbose_name = 'Списание инструмента'
        verbose_name_plural = 'Списания инструментов'
        ordering = ['-writeoff_date']

    def __str__(self):
        return f"Списание {self.tool} от {self.writeoff_date.strftime('%Y-%m-%d')}"
