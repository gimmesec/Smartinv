from rest_framework import serializers
from .models import ToolName, Tool, ToolTransferHistory


class ToolNameSerializer(serializers.ModelSerializer):
    """Сериализатор для названия инструмента."""
    class Meta:
        model = ToolName
        fields = ('id', 'name')


class ToolSerializer(serializers.ModelSerializer):
    """Сериализатор для инструмента."""
    tool_name_name = serializers.CharField(source='tool_name.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    current_object_name = serializers.CharField(
        source='current_object.name',
        read_only=True
    )

    class Meta:
        model = Tool
        fields = (
            'id', 'tool_name', 'tool_name_name', 'inventory_number', 'qr_code',
            'photo', 'current_object', 'current_object_name', 'status',
            'status_display', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class ToolListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка инструментов."""
    tool_name_name = serializers.CharField(source='tool_name.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Tool
        fields = (
            'id', 'tool_name_name', 'inventory_number', 'qr_code',
            'current_object', 'status', 'status_display'
        )


class ToolTransferHistorySerializer(serializers.ModelSerializer):
    """Сериализатор для истории перемещений инструмента."""
    tool_inventory_number = serializers.CharField(
        source='tool.inventory_number',
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

    class Meta:
        model = ToolTransferHistory
        fields = (
            'id', 'tool', 'tool_inventory_number', 'from_object', 'from_object_name',
            'to_object', 'to_object_name', 'transfer_date', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'transfer_date')
