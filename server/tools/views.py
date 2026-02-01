from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import ToolName, Tool, ToolTransferHistory
from .serializers import (
    ToolNameSerializer, ToolSerializer, ToolListSerializer,
    ToolTransferHistorySerializer
)
from users.permissions import IsAdminOrReadOnly
from users.models import UserRole


class ToolNameViewSet(viewsets.ModelViewSet):
    """ViewSet для названий инструментов."""
    queryset = ToolName.objects.all()
    serializer_class = ToolNameSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]


class ToolViewSet(viewsets.ModelViewSet):
    """ViewSet для инструментов."""
    queryset = Tool.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'current_object', 'tool_name']
    search_fields = ['inventory_number', 'qr_code', 'tool_name__name']
    ordering_fields = ['inventory_number', 'created_at']
    ordering = ['inventory_number']
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return ToolListSerializer
        return ToolSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.ADMIN:
            return Tool.objects.all()
        elif user.role == UserRole.FOREMAN:
            # Бригадир видит инструменты объектов, которыми управляет
            if user.assigned_object:
                return Tool.objects.filter(current_object=user.assigned_object)
            return Tool.objects.filter(current_object__in=user.managed_objects.all())
        else:
            # Рабочий видит инструменты своего объекта
            if user.assigned_object:
                return Tool.objects.filter(current_object=user.assigned_object)
            return Tool.objects.none()


class ToolTransferHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для истории перемещений инструментов (только чтение)."""
    queryset = ToolTransferHistory.objects.all()
    serializer_class = ToolTransferHistorySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['tool', 'from_object', 'to_object']
    ordering_fields = ['transfer_date']
    ordering = ['-transfer_date']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.ADMIN:
            return ToolTransferHistory.objects.all()
        elif user.role == UserRole.FOREMAN:
            # Бригадир видит историю объектов, которыми управляет
            return ToolTransferHistory.objects.filter(
                to_object__in=user.managed_objects.all()
            ) | ToolTransferHistory.objects.filter(
                from_object__in=user.managed_objects.all()
            )
        else:
            # Рабочий видит историю своего объекта
            if user.assigned_object:
                return ToolTransferHistory.objects.filter(
                    to_object=user.assigned_object
                ) | ToolTransferHistory.objects.filter(
                    from_object=user.assigned_object
                )
            return ToolTransferHistory.objects.none()
