from django.contrib import admin
from .models import WriteOff


@admin.register(WriteOff)
class WriteOffAdmin(admin.ModelAdmin):
    list_display = ('tool', 'user', 'writeoff_date', 'created_at')
    list_filter = ('writeoff_date',)
    search_fields = ('tool__inventory_number', 'tool__tool_name__name', 'user__full_name')
    readonly_fields = ('created_at', 'updated_at', 'writeoff_date')
    fieldsets = (
        ('Основная информация', {
            'fields': ('tool', 'user', 'writeoff_date')
        }),
        ('Документация', {
            'fields': ('broken_photo', 'qr_photo', 'description')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
