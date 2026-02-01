from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import WriteOff
from .serializers import WriteOffSerializer, WriteOffListSerializer
from users.permissions import IsForemanOrAdmin
from users.models import UserRole
from tools.models import Tool, ToolStatus


class WriteOffViewSet(viewsets.ModelViewSet):
    """ViewSet для списаний инструментов."""
    queryset = WriteOff.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['tool', 'user', 'writeoff_date']
    ordering_fields = ['writeoff_date', 'created_at']
    ordering = ['-writeoff_date']
    permission_classes = [IsAuthenticated, IsForemanOrAdmin]

    def get_serializer_class(self):
        if self.action == 'list':
            return WriteOffListSerializer
        return WriteOffSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.ADMIN:
            return WriteOff.objects.all()
        elif user.role == UserRole.FOREMAN:
            # Бригадир видит списания инструментов объектов, которыми управляет
            return WriteOff.objects.filter(
                tool__current_object__in=user.managed_objects.all()
            )
        return WriteOff.objects.none()

    def perform_create(self, serializer):
        writeoff = serializer.save(user=self.request.user)
        # Автоматически меняем статус инструмента на списан
        tool = writeoff.tool
        tool.status = ToolStatus.WRITTEN_OFF
        tool.save()
