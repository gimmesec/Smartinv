from django.contrib import admin

from .models import (
    Asset,
    AssetCategory,
    Employee,
    InventoryItem,
    InventorySession,
    LegalEntity,
    Location,
    OneCExchangeLog,
    Transfer,
    WriteOffAct,
)

admin.site.register(LegalEntity)
admin.site.register(Location)
admin.site.register(AssetCategory)
admin.site.register(Employee)
admin.site.register(Asset)
admin.site.register(InventorySession)
admin.site.register(InventoryItem)
admin.site.register(Transfer)
admin.site.register(WriteOffAct)
admin.site.register(OneCExchangeLog)
