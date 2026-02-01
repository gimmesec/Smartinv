from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админка для пользователей."""
    list_display = ('id', 'user_info', 'role', 'assigned_object', 'is_active', 'employment_date')
    list_display_links = ('id', 'user_info')
    list_filter = ('role', 'is_active', 'assigned_object')
    search_fields = ('username', 'full_name', 'id')
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    list_editable = ('assigned_object', 'is_active')
    
    def user_info(self, obj):
        """Отображение ФИО и username пользователя."""
        return format_html(
            '<strong>{}</strong><br><small style="color: #666;">ID: {} | Логин: {}</small>',
            obj.full_name,
            obj.id,
            obj.username
        )
    user_info.short_description = 'Пользователь'
    user_info.admin_order_field = 'full_name'

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {
            'fields': ('full_name', 'photo', 'role', 'employment_date', 'assigned_object')
        }),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Важные даты', {
            'fields': ('last_login', 'created_at', 'updated_at'),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'full_name', 'role'),
        }),
    )

    ordering = ('full_name',)
