from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import Transfer, TransferStatus
from .serializers import TransferSerializer, TransferListSerializer
from users.permissions import IsForemanOrAdmin
from users.models import UserRole
from tools.models import ToolTransferHistory, ToolStatus


class TransferViewSet(viewsets.ModelViewSet):
    """ViewSet для передач инструментов."""
    queryset = Transfer.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'from_object', 'to_object', 'foreman']
    ordering_fields = ['created_at', 'completed_at']
    ordering = ['-created_at']
    permission_classes = [IsAuthenticated, IsForemanOrAdmin]

    def get_serializer_class(self):
        if self.action == 'list':
            return TransferListSerializer
        return TransferSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.ADMIN:
            return Transfer.objects.all()
        elif user.role == UserRole.FOREMAN:
            # Бригадир видит передачи объектов, которыми управляет
            return Transfer.objects.filter(
                foreman=user
            ) | Transfer.objects.filter(
                from_object__in=user.managed_objects.all()
            ) | Transfer.objects.filter(
                to_object__in=user.managed_objects.all()
            )
        return Transfer.objects.none()

    def perform_create(self, serializer):
        serializer.save(foreman=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsForemanOrAdmin])
    def confirm(self, request, pk=None):
        """Подтвердить передачу."""
        transfer = self.get_object()
        if transfer.status != TransferStatus.CREATED:
            return Response(
                {'error': 'Можно подтвердить только созданную передачу'},
                status=status.HTTP_400_BAD_REQUEST
            )
        transfer.status = TransferStatus.CONFIRMED
        transfer.save()
        return Response({'status': 'Передача подтверждена'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsForemanOrAdmin])
    def reject(self, request, pk=None):
        """Отклонить передачу."""
        transfer = self.get_object()
        if transfer.status == TransferStatus.COMPLETED:
            return Response(
                {'error': 'Нельзя отклонить выполненную передачу'},
                status=status.HTTP_400_BAD_REQUEST
            )
        transfer.status = TransferStatus.REJECTED
        transfer.save()
        return Response({'status': 'Передача отклонена'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsForemanOrAdmin])
    def complete(self, request, pk=None):
        """Завершить передачу."""
        transfer = self.get_object()
        if transfer.status != TransferStatus.CONFIRMED:
            return Response(
                {'error': 'Можно завершить только подтвержденную передачу'},
                status=status.HTTP_400_BAD_REQUEST
            )
        transfer.status = TransferStatus.COMPLETED
        transfer.save()
        
        # Обновляем текущий объект инструмента
        transfer.tool.current_object = transfer.to_object
        transfer.tool.status = ToolStatus.IN_STOCK
        transfer.tool.save()
        
        # Создаем запись в истории перемещений
        ToolTransferHistory.objects.create(
            tool=transfer.tool,
            from_object=transfer.from_object,
            to_object=transfer.to_object
        )
        
        return Response({'status': 'Передача завершена'})
