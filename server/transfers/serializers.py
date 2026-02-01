from rest_framework import serializers
from .models import Transfer


class TransferSerializer(serializers.ModelSerializer):
    """Сериализатор для передачи инструмента."""
    tool_inventory_number = serializers.CharField(
        source='tool.inventory_number',
        read_only=True
    )
    tool_name = serializers.CharField(
        source='tool.tool_name.name',
        read_only=True
    )
    from_object_name = serializers.CharField(
        source='from_object.name',
        read_only=True
    )
    to_object_name = serializers.CharField(
        source='to_object.name',
        read_only=True
    )
    foreman_full_name = serializers.CharField(
        source='foreman.full_name',
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Transfer
        fields = (
            'id', 'tool', 'tool_inventory_number', 'tool_name',
            'from_object', 'from_object_name', 'to_object', 'to_object_name',
            'foreman', 'foreman_full_name', 'status', 'status_display',
            'created_at', 'completed_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'completed_at')


class TransferListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка передач."""
    tool_inventory_number = serializers.CharField(
        source='tool.inventory_number',
        read_only=True
    )
    to_object_name = serializers.CharField(
        source='to_object.name',
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Transfer
        fields = (
            'id', 'tool_inventory_number', 'from_object', 'to_object',
            'to_object_name', 'status', 'status_display', 'created_at'
        )
