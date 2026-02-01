from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import Inventory, InventoryTool
from .serializers import InventorySerializer, InventoryListSerializer
from users.permissions import IsForemanOrAdmin
from users.models import UserRole


class InventoryViewSet(viewsets.ModelViewSet):
    """ViewSet для инвентаризаций."""
    queryset = Inventory.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['object', 'user', 'date']
    ordering_fields = ['date', 'created_at']
    ordering = ['-date']
    permission_classes = [IsAuthenticated, IsForemanOrAdmin]

    def get_serializer_class(self):
        if self.action == 'list':
            return InventoryListSerializer
        return InventorySerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.ADMIN:
            return Inventory.objects.all()
        elif user.role == UserRole.FOREMAN:
            # Бригадир видит инвентаризации объектов, которыми управляет
            return Inventory.objects.filter(
                object__in=user.managed_objects.all()
            )
        return Inventory.objects.none()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
