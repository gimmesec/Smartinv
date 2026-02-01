from rest_framework import serializers
from .models import WriteOff


class WriteOffSerializer(serializers.ModelSerializer):
    """Сериализатор для списания инструмента."""
    tool_inventory_number = serializers.CharField(
        source='tool.inventory_number',
        read_only=True
    )
    tool_name = serializers.CharField(
        source='tool.tool_name.name',
        read_only=True
    )
    user_full_name = serializers.CharField(
        source='user.full_name',
        read_only=True
    )

    class Meta:
        model = WriteOff
        fields = (
            'id', 'tool', 'tool_inventory_number', 'tool_name',
            'broken_photo', 'qr_photo', 'description', 'user', 'user_full_name',
            'writeoff_date', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'writeoff_date')


class WriteOffListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка списаний."""
    tool_inventory_number = serializers.CharField(
        source='tool.inventory_number',
        read_only=True
    )
    tool_name = serializers.CharField(
        source='tool.tool_name.name',
        read_only=True
    )

    class Meta:
        model = WriteOff
        fields = (
            'id', 'tool_inventory_number', 'tool_name', 'user', 'writeoff_date'
        )
