from django.db import models
from django.contrib.auth.models import AbstractUser

# -----------------------
# Роли пользователей
# -----------------------
class Role(models.Model):
    """
    Роль пользователя в системе.
    Примеры: Рабочий, Бригадир, Администратор.
    """
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


# -----------------------
# Строительные объекты
# -----------------------
class Object(models.Model):
    """
    Строительный объект, к которому привязаны рабочие и бригадиры.
    """
    name = models.CharField(max_length=255, unique=True)
    city = models.CharField(max_length=255, blank=True)       # Город
    address = models.CharField(max_length=255, blank=True)    # Адрес
    foremen = models.ManyToManyField(
        'User',
        related_name='managed_objects',
        blank=True
    )  # бригадиры объекта

    def __str__(self):
        return f"{self.name} ({self.city})"


# -----------------------
# Пользователи системы
# -----------------------
class User(AbstractUser):
    """
    Пользователь системы (рабочий, бригадир, администратор и т.д.)
    Наследуется от AbstractUser для работы с аутентификацией Django.
    """
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    photo = models.ImageField(upload_to='users/', null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='users')
    employment_date = models.DateField(null=True, blank=True)
    assigned_object = models.ForeignKey(
        Object,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )

    # Дополнительные служебные поля
    chat_id = models.BigIntegerField(null=True, blank=True)  # Telegram chat_id для уведомлений
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    # Переопределяем username для уникальности
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'full_name']

    def __str__(self):
        return self.full_name
