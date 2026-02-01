from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import ConstructionObject
from .serializers import ConstructionObjectSerializer, ConstructionObjectListSerializer
from users.permissions import IsAdminOrReadOnly, IsForemanOrAdmin
from users.models import UserRole


class ConstructionObjectViewSet(viewsets.ModelViewSet):
    """ViewSet для строительных объектов."""
    queryset = ConstructionObject.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'city']
    search_fields = ['name', 'city', 'address']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'list':
            return ConstructionObjectListSerializer
        return ConstructionObjectSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.ADMIN:
            return ConstructionObject.objects.all()
        elif user.role == UserRole.FOREMAN:
            # Бригадир видит объекты, которыми управляет
            return user.managed_objects.all()
        else:
            # Рабочий видит только свой объект
            if user.assigned_object:
                return ConstructionObject.objects.filter(id=user.assigned_object.id)
            return ConstructionObject.objects.none()
