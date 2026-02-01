from django.db import models


class AuditMixin(models.Model):
    """Базовый миксин для audit-полей created_at и updated_at."""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        abstract = True
