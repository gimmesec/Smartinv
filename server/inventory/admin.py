from django.contrib import admin
from .models import Inventory, InventoryTool


class InventoryToolInline(admin.TabularInline):
    model = InventoryTool
    extra = 1


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('object', 'user', 'date', 'created_at')
    list_filter = ('date', 'object')
    search_fields = ('object__name', 'user__full_name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [InventoryToolInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('date', 'object', 'user')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(InventoryTool)
class InventoryToolAdmin(admin.ModelAdmin):
    list_display = ('inventory', 'tool', 'is_present')
    list_filter = ('is_present', 'inventory__date')
    search_fields = ('tool__inventory_number', 'tool__tool_name__name', 'inventory__object__name')
