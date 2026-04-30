from rest_framework import serializers
from django.db import DatabaseError
from django.core.files.storage import default_storage

from .models import (
    Asset,
    AssetCategory,
    AssetConditionJob,
    Employee,
    InventoryItem,
    InventorySession,
    LegalEntity,
    Location,
    OneCExchangeLog,
    Transfer,
    WriteOffAct,
)


class LegalEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalEntity
        fields = "__all__"


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = "__all__"


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = "__all__"


class AssetConditionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetConditionJob
        fields = (
            "id",
            "asset",
            "status",
            "vision_result",
            "llm_summary",
            "error_message",
            "source_image",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "asset",
            "status",
            "vision_result",
            "llm_summary",
            "error_message",
            "source_image",
            "created_at",
            "updated_at",
        )


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = "__all__"


class AssetSerializer(serializers.ModelSerializer):
    def _resolve_latest_photo_url(self, obj: Asset):
        try:
            latest_inventory_photo = obj.inventory_photos.order_by("-created_at").values_list("photo", flat=True).first()
            if latest_inventory_photo:
                return default_storage.url(latest_inventory_photo)
        except DatabaseError:
            # Backward-compatible fallback while migration for AssetPhoto
            # is not yet applied in the runtime database.
            pass
        return obj.photo.url if obj.photo else None

    def to_representation(self, instance: Asset):
        data = super().to_representation(instance)
        data["photo"] = self._resolve_latest_photo_url(instance)
        return data

    def validate(self, attrs):
        legal_entity = attrs.get("legal_entity") or getattr(self.instance, "legal_entity", None)
        employee = attrs.get("responsible_employee") if "responsible_employee" in attrs else getattr(
            self.instance, "responsible_employee", None
        )
        location = attrs.get("location") if "location" in attrs else getattr(self.instance, "location", None)

        if not employee and not location:
            raise serializers.ValidationError("Актив должен быть закреплен за сотрудником или локацией.")

        if legal_entity and employee and employee.legal_entity_id != legal_entity.id:
            raise serializers.ValidationError("Сотрудник и актив должны принадлежать одному юрлицу.")

        if legal_entity and location and location.legal_entity_id != legal_entity.id:
            raise serializers.ValidationError("Локация и актив должны принадлежать одному юрлицу.")

        return attrs

    class Meta:
        model = Asset
        fields = "__all__"


class InventorySessionSerializer(serializers.ModelSerializer):
    legal_entity_name = serializers.CharField(source="legal_entity.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True, allow_null=True)

    class Meta:
        model = InventorySession
        fields = (
            "id",
            "created_at",
            "updated_at",
            "legal_entity",
            "legal_entity_name",
            "location",
            "location_name",
            "started_by",
            "conducted_by_employees",
            "status",
            "started_at",
            "finished_at",
            "external_1c_id",
        )


class InventoryItemSerializer(serializers.ModelSerializer):
    """`asset` — id для записи; `asset_detail` — полный объект (чтобы клиент не терял активы при длинных списках)."""

    asset_detail = AssetSerializer(source="asset", read_only=True)

    class Meta:
        model = InventoryItem
        fields = (
            "id",
            "session",
            "asset",
            "asset_detail",
            "scanned_at",
            "detected",
            "detected_inventory_number",
            "ocr_text",
            "condition",
            "ai_condition",
            "ai_confidence",
            "ai_provider",
            "ai_comment",
            "comment",
            "photo",
            "created_at",
            "updated_at",
        )


class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = "__all__"


class WriteOffActSerializer(serializers.ModelSerializer):
    class Meta:
        model = WriteOffAct
        fields = "__all__"


class OneCExchangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OneCExchangeLog
        fields = "__all__"
        read_only_fields = ("id", "direction", "status", "payload", "response", "error_message", "created_at", "updated_at")
