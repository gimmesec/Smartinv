from django.contrib import admin
from .models import ConstructionObject


@admin.register(ConstructionObject)
class ConstructionObjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'address', 'is_active', 'created_at')
    list_filter = ('is_active', 'city')
    search_fields = ('name', 'city', 'address')
    readonly_fields = ('created_at', 'updated_at')
