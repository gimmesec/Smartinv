from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import path

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
from .services import export_to_1c_xml, import_from_1c_xml


class XMLImportForm(forms.Form):
    xml_file = forms.FileField(required=False, label="XML файл")
    xml_text = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 12}), label="XML текст")

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("xml_file") and not (cleaned.get("xml_text") or "").strip():
            raise forms.ValidationError("Загрузите XML файл или вставьте XML текст.")
        return cleaned


@admin.register(LegalEntity)
class LegalEntityAdmin(admin.ModelAdmin):
    list_display = ("name", "tax_id", "kpp", "external_1c_id")
    search_fields = ("name", "tax_id", "external_1c_id")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "legal_entity", "external_1c_id")
    list_filter = ("type", "legal_entity")
    search_fields = ("name", "external_1c_id")


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "position", "legal_entity", "user", "external_1c_id")
    search_fields = ("full_name", "position", "external_1c_id", "user__username", "user__email")
    autocomplete_fields = ("user",)


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("inventory_number", "name", "status", "legal_entity", "external_1c_id")
    list_filter = ("status", "legal_entity")
    search_fields = ("inventory_number", "name", "external_1c_id")


@admin.register(InventorySession)
class InventorySessionAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "legal_entity", "started_at", "finished_at", "conductors")
    list_filter = ("status", "legal_entity")
    filter_horizontal = ("conducted_by_employees",)

    def conductors(self, obj):
        return ", ".join(obj.conducted_by_employees.values_list("full_name", flat=True)) or "-"

    conductors.short_description = "Проводили"


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "asset", "condition", "scanned_at")
    list_filter = ("condition",)


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ("id", "asset", "transfer_date", "status")
    list_filter = ("status",)


@admin.register(WriteOffAct)
class WriteOffActAdmin(admin.ModelAdmin):
    list_display = ("id", "asset", "legal_entity", "status", "wear_level_percent")
    list_filter = ("status", "legal_entity")


@admin.register(OneCExchangeLog)
class OneCExchangeLogAdmin(admin.ModelAdmin):
    list_display = ("id", "direction", "status", "created_at")
    list_filter = ("direction", "status")
    readonly_fields = ("payload", "response", "error_message", "created_at", "updated_at")
    change_list_template = "admin/inventory/onecexchangelog/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-xml/",
                self.admin_site.admin_view(self.import_xml_view),
                name="inventory_onecexchangelog_import_xml",
            ),
            path(
                "export-xml/",
                self.admin_site.admin_view(self.export_xml_view),
                name="inventory_onecexchangelog_export_xml",
            ),
        ]
        return custom_urls + urls

    def has_add_permission(self, request):
        # Logs are created automatically during import/export.
        return False

    def has_change_permission(self, request, obj=None):
        # Keep log entries read-only in admin.
        if obj is None:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def import_xml_view(self, request):
        form = XMLImportForm(request.POST or None, request.FILES or None)
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Импорт XML из 1С",
            "form": form,
        }

        if request.method == "POST" and form.is_valid():
            xml_payload = (form.cleaned_data.get("xml_text") or "").strip()
            xml_file = form.cleaned_data.get("xml_file")
            if xml_file and not xml_payload:
                xml_payload = xml_file.read().decode("utf-8", errors="ignore")
            try:
                result = import_from_1c_xml(xml_payload)
                messages.success(request, f"Импорт завершен: {result}")
            except Exception as exc:
                messages.error(request, f"Ошибка импорта: {exc}")
            return TemplateResponse(request, "admin/inventory/xml_import.html", context)

        return TemplateResponse(request, "admin/inventory/xml_import.html", context)

    def export_xml_view(self, request):
        xml_payload = export_to_1c_xml()
        response = HttpResponse(xml_payload, content_type="application/xml; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="smartinv_export.xml"'
        messages.success(request, "XML экспорт успешно сформирован.")
        return response
