from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Asset,
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


class LegalEntityViewSet(viewsets.ModelViewSet):
    queryset = LegalEntity.objects.all().order_by("-created_at")
    serializer_class = LegalEntitySerializer


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.select_related("legal_entity", "parent").all().order_by("-created_at")
    serializer_class = LocationSerializer


class AssetCategoryViewSet(viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all().order_by("name")
    serializer_class = AssetCategorySerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related("legal_entity").all().order_by("full_name")
    serializer_class = EmployeeSerializer


class AssetViewSet(viewsets.ModelViewSet):
    queryset = (
        Asset.objects.select_related("legal_entity", "location", "category", "responsible_employee")
        .all()
        .order_by("-created_at")
    )
    serializer_class = AssetSerializer

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
    queryset = InventorySession.objects.select_related("legal_entity", "location", "started_by").all()
    serializer_class = InventorySessionSerializer


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.select_related("session", "asset").all()
    serializer_class = InventoryItemSerializer


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


class InventoryAIAnalyzeAPIView(APIView):
    @extend_schema(
        summary="ИИ-оценка состояния актива по результату сканирования",
        description="Обновляет ai_condition/ai_confidence для записи инвентаризации на основе OCR и комментария.",
        responses={200: OpenApiResponse(description="Оценка выполнена")},
    )
    def post(self, request, item_id: int):
        try:
            item = InventoryItem.objects.get(id=item_id)
        except InventoryItem.DoesNotExist:
            return Response({"detail": "Inventory item not found"}, status=status.HTTP_404_NOT_FOUND)

        result = assess_inventory_item_with_ai(item)
        return Response(result, status=status.HTTP_200_OK)
