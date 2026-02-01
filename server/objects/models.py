from django.db import models
from common.models import AuditMixin


class ConstructionObject(AuditMixin):
    """Строительный объект."""
    name = models.CharField(max_length=255, verbose_name='Название')
    city = models.CharField(max_length=255, verbose_name='Город')
    address = models.CharField(max_length=255, verbose_name='Адрес')
    foremen = models.ManyToManyField(
        'users.User',
        related_name='managed_objects',
        blank=True,
        verbose_name='Бригадиры',
        limit_choices_to={'role': 'foreman'}
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Строительный объект'
        verbose_name_plural = 'Строительные объекты'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.city})"
