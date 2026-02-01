from django.contrib import admin
from .models import Transfer


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('tool', 'from_object', 'to_object', 'foreman', 'status', 'created_at', 'completed_at')
    list_filter = ('status', 'created_at', 'from_object', 'to_object')
    search_fields = ('tool__inventory_number', 'tool__tool_name__name', 'foreman__full_name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('tool', 'from_object', 'to_object', 'foreman')
        }),
        ('Статус', {
            'fields': ('status', 'created_at', 'completed_at')
        }),
        ('Системная информация', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
