from rest_framework import serializers
from .models import ConstructionObject


class ConstructionObjectSerializer(serializers.ModelSerializer):
    """Сериализатор для строительного объекта."""
    foremen_count = serializers.IntegerField(source='foremen.count', read_only=True)
    users_count = serializers.IntegerField(source='users.count', read_only=True)

    class Meta:
        model = ConstructionObject
        fields = (
            'id', 'name', 'city', 'address', 'foremen', 'is_active',
            'foremen_count', 'users_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class ConstructionObjectListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка объектов."""
    foremen_count = serializers.IntegerField(source='foremen.count', read_only=True)

    class Meta:
        model = ConstructionObject
        fields = ('id', 'name', 'city', 'address', 'is_active', 'foremen_count')
