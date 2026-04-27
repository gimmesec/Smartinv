from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from .models import (
    Asset,
    AssetPhoto,
    AssetCategory,
    Employee,
    InventoryItem,
    InventorySession,
    LegalEntity,
    Location,
    OneCExchangeLog,
    Transfer,
    WriteOffAct,
)
from .serializers import (
    AssetCategorySerializer,
    AssetSerializer,
    EmployeeSerializer,
    InventoryItemSerializer,
    InventorySessionSerializer,
    LegalEntitySerializer,
    LocationSerializer,
    OneCExchangeLogSerializer,
    TransferSerializer,
    WriteOffActSerializer,
)
from .services import assess_inventory_item_with_ai, export_to_1c_xml, import_from_1c_xml


def get_employee_for_user(user):
    if not user or not user.is_authenticated:
        return None
    return Employee.objects.select_related("legal_entity").filter(user=user).first()


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


class LegalEntityViewSet(viewsets.ModelViewSet):
    serializer_class = LegalEntitySerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = LegalEntity.objects.all().order_by("-created_at")
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return queryset
        employee = get_employee_for_user(user)
        if not employee:
            return queryset.none()
        return queryset.filter(id=employee.legal_entity_id)


class LocationViewSet(viewsets.ModelViewSet):
    serializer_class = LocationSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = Location.objects.select_related("legal_entity", "parent").all().order_by("-created_at")
        user = self.request.user
        if not (user.is_staff or user.is_superuser):
            employee = get_employee_for_user(user)
            if not employee:
                return queryset.none()
            queryset = queryset.filter(legal_entity_id=employee.legal_entity_id)
        legal_entity_id = self.request.query_params.get("legal_entity")
        parent_id = self.request.query_params.get("parent")
        if legal_entity_id:
            queryset = queryset.filter(legal_entity_id=legal_entity_id)
        if parent_id == "null":
            queryset = queryset.filter(parent__isnull=True)
        elif parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        return queryset


class AssetCategoryViewSet(viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all().order_by("name")
    serializer_class = AssetCategorySerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = Employee.objects.select_related("legal_entity", "user").all().order_by("full_name")
        user = self.request.user
        if not (user.is_staff or user.is_superuser):
            employee = get_employee_for_user(user)
            if not employee:
                return queryset.none()
            queryset = queryset.filter(legal_entity_id=employee.legal_entity_id)

        legal_entity_id = self.request.query_params.get("legal_entity")
        if legal_entity_id:
            queryset = queryset.filter(legal_entity_id=legal_entity_id)
        return queryset


class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = (
            Asset.objects.select_related("legal_entity", "location", "category", "responsible_employee")
            .prefetch_related("inventory_photos")
            .all()
            .order_by("-created_at")
        )
        user = self.request.user
        if not (user.is_staff or user.is_superuser):
            employee = get_employee_for_user(user)
            if not employee:
                return queryset.none()
            queryset = queryset.filter(legal_entity_id=employee.legal_entity_id)

        legal_entity_id = self.request.query_params.get("legal_entity")
        location_id = self.request.query_params.get("location")
        responsible_employee_id = self.request.query_params.get("responsible_employee")
        if legal_entity_id:
            queryset = queryset.filter(legal_entity_id=legal_entity_id)
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        if responsible_employee_id:
            queryset = queryset.filter(responsible_employee_id=responsible_employee_id)
        return queryset

    @action(detail=False, methods=["get"], url_path="my-responsible")
    def my_responsible(self, request):
        employee = get_employee_for_user(request.user)
        if not employee:
            return Response([])
        queryset = self.get_queryset().filter(responsible_employee_id=employee.id)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=["post"], url_path="write-off")
    def write_off(self, request, pk=None):
        asset = self.get_object()
        reason = request.data.get("reason", "").strip()
        try:
            wear_level_percent = int(request.data.get("wear_level_percent", 0))
        except (TypeError, ValueError):
            return Response({"detail": "wear_level_percent must be integer"}, status=status.HTTP_400_BAD_REQUEST)
        if not reason:
            return Response({"detail": "reason is required"}, status=status.HTTP_400_BAD_REQUEST)

        act = WriteOffAct.objects.create(
            asset=asset,
            legal_entity=asset.legal_entity,
            reason=reason,
            wear_level_percent=wear_level_percent,
            created_by=request.user if request.user.is_authenticated else None,
            status=WriteOffAct.WriteOffStatus.CONFIRMED,
        )
        asset.status = Asset.AssetStatus.WRITTEN_OFF
        asset.save(update_fields=["status", "updated_at"])
        return Response(WriteOffActSerializer(act).data, status=status.HTTP_201_CREATED)


class InventorySessionViewSet(viewsets.ModelViewSet):
    serializer_class = InventorySessionSerializer

    def get_queryset(self):
        queryset = InventorySession.objects.select_related("legal_entity", "location", "started_by").all()
        legal_entity_id = self.request.query_params.get("legal_entity")
        status_value = self.request.query_params.get("status")
        if legal_entity_id:
            queryset = queryset.filter(legal_entity_id=legal_entity_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return queryset
        employee = get_employee_for_user(user)
        if not employee:
            return queryset.none()
        return queryset.filter(legal_entity_id=employee.legal_entity_id)

    @action(detail=True, methods=["post"], url_path="conduct")
    def conduct(self, request, pk=None):
        session = self.get_object()
        legal_entity_id = request.data.get("legal_entity_id")
        if not legal_entity_id:
            return Response({"detail": "legal_entity_id обязателен."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            legal_entity_id_int = int(legal_entity_id)
        except (TypeError, ValueError):
            return Response({"detail": "legal_entity_id должен быть числом."}, status=status.HTTP_400_BAD_REQUEST)
        if legal_entity_id_int != session.legal_entity_id:
            return Response({"detail": "legal_entity_id должен совпадать с юрлицом выбранной сессии."}, status=status.HTTP_400_BAD_REQUEST)

        is_admin = bool(request.user and (request.user.is_staff or request.user.is_superuser))
        employee_ids = request.data.get("employee_ids") or []
        if isinstance(employee_ids, int):
            employee_ids = [employee_ids]
        if not isinstance(employee_ids, list):
            return Response({"detail": "employee_ids должен быть списком id сотрудников."}, status=status.HTTP_400_BAD_REQUEST)

        selected_employees = []
        if is_admin:
            if employee_ids:
                selected_employees = list(
                    Employee.objects.select_related("user")
                    .filter(id__in=employee_ids, legal_entity_id=session.legal_entity_id)
                    .distinct()
                )
                if len(selected_employees) != len(set(employee_ids)):
                    return Response(
                        {"detail": "Все выбранные сотрудники должны существовать и принадлежать юрлицу сессии."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        else:
            employee = get_employee_for_user(request.user)
            if not employee:
                return Response({"detail": "Сотрудник для текущего пользователя не найден."}, status=status.HTTP_400_BAD_REQUEST)
            if employee.legal_entity_id != session.legal_entity_id:
                return Response({"detail": "Сотрудник не относится к юрлицу сессии."}, status=status.HTTP_403_FORBIDDEN)
            selected_employees = [employee]

        started_by = request.user
        first_with_user = next((emp for emp in selected_employees if emp.user_id), None)
        if first_with_user:
            started_by = first_with_user.user

        session.legal_entity_id = legal_entity_id_int
        session.started_by = started_by
        if session.status == InventorySession.SessionStatus.DRAFT:
            session.status = InventorySession.SessionStatus.IN_PROGRESS
        session.save(update_fields=["legal_entity", "started_by", "status", "updated_at"])
        if selected_employees:
            session.conducted_by_employees.set(selected_employees)
        else:
            session.conducted_by_employees.clear()
        return Response(self.get_serializer(session).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        session = self.get_object()
        if session.status == InventorySession.SessionStatus.COMPLETED:
            return Response(self.get_serializer(session).data, status=status.HTTP_200_OK)
        session.status = InventorySession.SessionStatus.COMPLETED
        session.finished_at = timezone.now()
        session.save(update_fields=["status", "finished_at", "updated_at"])
        return Response(self.get_serializer(session).data, status=status.HTTP_200_OK)


class InventoryItemViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryItemSerializer

    def get_queryset(self):
        queryset = InventoryItem.objects.select_related("session", "asset").all()
        session_id = self.request.query_params.get("session")
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return queryset
        employee = get_employee_for_user(user)
        if not employee:
            return queryset.none()
        return queryset.filter(asset__legal_entity_id=employee.legal_entity_id)

    def _sync_asset_last_photo(self, item: InventoryItem, previous_photo_name: str | None = None):
        if not item.photo:
            return
        current_name = item.photo.name
        if previous_photo_name == current_name:
            return
        AssetPhoto.objects.create(
            asset=item.asset,
            session=item.session,
            inventory_item=item,
            photo=item.photo,
        )
        item.asset.photo = item.photo
        item.asset.save(update_fields=["photo", "updated_at"])

    def perform_create(self, serializer):
        item = serializer.save()
        self._sync_asset_last_photo(item)

    def perform_update(self, serializer):
        previous_photo_name = serializer.instance.photo.name if serializer.instance.photo else None
        item = serializer.save()
        self._sync_asset_last_photo(item, previous_photo_name=previous_photo_name)


class TransferViewSet(viewsets.ModelViewSet):
    queryset = Transfer.objects.select_related("asset", "from_employee", "to_employee").all()
    serializer_class = TransferSerializer


class WriteOffActViewSet(viewsets.ModelViewSet):
    queryset = WriteOffAct.objects.select_related("asset", "legal_entity").all().order_by("-created_at")
    serializer_class = WriteOffActSerializer


class OneCExchangeLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OneCExchangeLog.objects.all().order_by("-created_at")
    serializer_class = OneCExchangeLogSerializer


class OneCImportAPIView(APIView):
    @extend_schema(
        summary="Импорт XML из 1С УНФ",
        description="Принимает XML пакет и синхронизирует юрлица и активы в SmartInv.",
        request={"application/xml": {"type": "string"}},
        responses={
            200: OpenApiResponse(description="Импорт выполнен"),
            400: OpenApiResponse(description="Ошибка формата"),
        },
        examples=[
            OpenApiExample(
                "Пример XML",
                value=(
                    "<exchange><legal_entities><legal_entity id='e1' name='ООО Ромашка' tax_id='7701234567' />"
                    "</legal_entities><assets><asset id='a1' name='Ноутбук Lenovo' "
                    "inventory_number='INV-0001' legal_entity_id='e1' status='active' /></assets></exchange>"
                ),
                request_only=True,
            )
        ],
    )
    def post(self, request):
        xml_payload = request.body.decode("utf-8", errors="ignore")
        if not xml_payload:
            return Response({"detail": "XML payload is empty"}, status=status.HTTP_400_BAD_REQUEST)
        result = import_from_1c_xml(xml_payload)
        return Response(result, status=status.HTTP_200_OK)


class OneCExportAPIView(APIView):
    @extend_schema(
        summary="Экспорт XML в 1С УНФ",
        description="Формирует XML пакет текущего состояния юрлиц и активов.",
        responses={200: OpenApiResponse(description="XML пакет")},
    )
    def get(self, request):
        xml_payload = export_to_1c_xml()
        return Response({"xml": xml_payload}, status=status.HTTP_200_OK)


class InventoryAIAnalyzeResponseSerializer(serializers.Serializer):
    inventory_item_id = serializers.IntegerField()
    ai_provider = serializers.CharField()
    ai_condition = serializers.CharField()
    ai_confidence = serializers.FloatField()
    ai_comment = serializers.CharField()


class InventoryAIAnalyzeAPIView(APIView):
    @extend_schema(
        summary="ИИ-оценка состояния актива по результату сканирования",
        description="Обновляет ai_condition/ai_confidence для записи инвентаризации на основе OCR и комментария.",
        request=None,
        responses={200: InventoryAIAnalyzeResponseSerializer},
    )
    def post(self, request, item_id: int):
        try:
            item = InventoryItem.objects.get(id=item_id)
        except InventoryItem.DoesNotExist:
            return Response({"detail": "Inventory item not found"}, status=status.HTTP_404_NOT_FOUND)

        result = assess_inventory_item_with_ai(item)
        return Response(result, status=status.HTTP_200_OK)


class CurrentUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Текущий пользователь",
        description="Возвращает профиль текущего пользователя и признаки admin-роли.",
        responses={200: OpenApiResponse(description="Профиль пользователя")},
    )
    def get(self, request):
        user = request.user
        employee = get_employee_for_user(user)
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "is_admin": bool(user.is_staff or user.is_superuser),
                "employee_id": employee.id if employee else None,
                "employee_name": employee.full_name if employee else "",
                "legal_entity_id": employee.legal_entity_id if employee else None,
                "legal_entity_name": employee.legal_entity.name if employee else "",
            }
        )
