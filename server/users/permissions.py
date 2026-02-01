from rest_framework import permissions
from .models import UserRole


class IsAdminOrReadOnly(permissions.BasePermission):
    """Разрешение только для администраторов на изменение, остальные - только чтение."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role == UserRole.ADMIN


class IsAdmin(permissions.BasePermission):
    """Разрешение только для администраторов."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.ADMIN


class IsForemanOrAdmin(permissions.BasePermission):
    """Разрешение для бригадиров и администраторов."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in [UserRole.ADMIN, UserRole.FOREMAN]
        )


class IsOwnerOrForemanOrAdmin(permissions.BasePermission):
    """Разрешение для владельца объекта, бригадира или администратора."""
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == UserRole.ADMIN:
            return True
        if user.role == UserRole.FOREMAN:
            # Бригадир может видеть данные своей бригады и объекта
            if hasattr(obj, 'assigned_object') and obj.assigned_object:
                return obj.assigned_object in user.managed_objects.all()
            if hasattr(obj, 'object') and obj.object:
                return obj.object in user.managed_objects.all()
        if user.role == UserRole.WORKER:
            # Рабочий может видеть только свои данные
            return obj == user or (hasattr(obj, 'user') and obj.user == user)
        return False
