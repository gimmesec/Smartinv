from rest_framework import serializers
from .models import User, UserRole


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    assigned_object_name = serializers.CharField(
        source='assigned_object.name',
        read_only=True
    )

    class Meta:
        model = User
        fields = (
            'id', 'username', 'full_name', 'photo', 'role', 'role_display',
            'employment_date', 'assigned_object', 'assigned_object_name',
            'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка пользователей."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'full_name', 'role', 'role_display', 'assigned_object', 'is_active')
