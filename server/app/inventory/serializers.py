from rest_framework import serializers

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


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = "__all__"


class AssetSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = InventorySession
        fields = "__all__"


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = "__all__"


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
        read_only_fields = "__all__"
