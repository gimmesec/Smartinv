from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from common.models import AuditMixin


class UserRole(models.TextChoices):
    """Роли пользователей в системе."""
    ADMIN = 'admin', 'Администратор'
    FOREMAN = 'foreman', 'Бригадир'
    WORKER = 'worker', 'Рабочий'


class UserManager(BaseUserManager):
    """Менеджер для модели User."""

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, AuditMixin):
    """
    Пользователь системы.
    Хранит только необходимые персональные данные согласно требованиям ПДн:
    - ФИО
    - Фотография
    - Роль
    - Дата трудоустройства
    - Объект закрепления
    """
    username = models.CharField(max_length=150, unique=True, verbose_name='Логин')
    full_name = models.CharField(max_length=255, verbose_name='ФИО')
    photo = models.ImageField(upload_to='users/', null=True, blank=True, verbose_name='Фотография')
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.WORKER,
        verbose_name='Роль'
    )
    employment_date = models.DateField(null=True, blank=True, verbose_name='Дата трудоустройства')
    assigned_object = models.ForeignKey(
        'objects.ConstructionObject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Объект закрепления'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    is_staff = models.BooleanField(default=False, verbose_name='Доступ к админке')

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['full_name']

    def __str__(self):
        return self.full_name

    @property
    def is_admin(self):
        """Проверка, является ли пользователь администратором."""
        return self.role == UserRole.ADMIN

    @property
    def is_foreman(self):
        """Проверка, является ли пользователь бригадиром."""
        return self.role == UserRole.FOREMAN

    @property
    def is_worker(self):
        """Проверка, является ли пользователь рабочим."""
        return self.role == UserRole.WORKER
