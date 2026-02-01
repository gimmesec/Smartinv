from django.contrib import admin
from .models import ToolName, Tool, ToolTransferHistory


@admin.register(ToolName)
class ToolNameAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ('inventory_number', 'tool_name', 'status', 'current_object', 'created_at')
    list_filter = ('status', 'current_object', 'tool_name')
    search_fields = ('inventory_number', 'qr_code', 'tool_name__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('tool_name', 'inventory_number', 'qr_code', 'photo')
        }),
        ('Расположение и статус', {
            'fields': ('current_object', 'status')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ToolTransferHistory)
class ToolTransferHistoryAdmin(admin.ModelAdmin):
    list_display = ('tool', 'from_object', 'to_object', 'transfer_date')
    list_filter = ('transfer_date', 'to_object', 'from_object')
    search_fields = ('tool__inventory_number', 'tool__tool_name__name')
    readonly_fields = ('created_at', 'updated_at', 'transfer_date')
