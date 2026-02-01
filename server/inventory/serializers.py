from rest_framework import serializers
from .models import Inventory, InventoryTool


class InventoryToolSerializer(serializers.ModelSerializer):
    """Сериализатор для инструмента в инвентаризации."""
    tool_inventory_number = serializers.CharField(
        source='tool.inventory_number',
        read_only=True
    )
    tool_name = serializers.CharField(
        source='tool.tool_name.name',
        read_only=True
    )

    class Meta:
        model = InventoryTool
        fields = ('id', 'tool', 'tool_inventory_number', 'tool_name', 'is_present')


class InventorySerializer(serializers.ModelSerializer):
    """Сериализатор для инвентаризации."""
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    object_name = serializers.CharField(source='object.name', read_only=True)
    inventory_tools = InventoryToolSerializer(many=True, read_only=True)

    class Meta:
        model = Inventory
        fields = (
            'id', 'date', 'object', 'object_name', 'user', 'user_full_name',
            'tools', 'inventory_tools', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class InventoryListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка инвентаризаций."""
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    object_name = serializers.CharField(source='object.name', read_only=True)
    tools_count = serializers.IntegerField(source='tools.count', read_only=True)

    class Meta:
        model = Inventory
        fields = ('id', 'date', 'object', 'object_name', 'user_full_name', 'tools_count')
