from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import User, UserRole
from .serializers import UserSerializer, UserListSerializer
from .permissions import IsAdmin, IsOwnerOrForemanOrAdmin


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet для пользователей."""
    queryset = User.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active', 'assigned_object']
    search_fields = ['username', 'full_name']
    ordering_fields = ['full_name', 'employment_date', 'created_at']
    ordering = ['full_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdmin]
        elif self.action == 'retrieve':
            permission_classes = [IsAuthenticated, IsOwnerOrForemanOrAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.ADMIN:
            return User.objects.all()
        elif user.role == UserRole.FOREMAN:
            # Бригадир видит пользователей своего объекта
            if user.assigned_object:
                return User.objects.filter(assigned_object=user.assigned_object)
            return User.objects.none()
        else:
            # Рабочий видит только себя
            return User.objects.filter(id=user.id)

    @action(detail=False, methods=['get', 'delete'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Получить или удалить данные текущего пользователя."""
        if request.method == 'DELETE':
            # Пользователь может удалить свой аккаунт
            user = request.user
            user.is_active = False
            user.save()
            return Response(
                {'message': 'Ваш аккаунт успешно деактивирован'},
                status=status.HTTP_200_OK
            )
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
