from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssetCategoryViewSet,
    AssetViewSet,
    EmployeeViewSet,
    InventoryItemViewSet,
    InventorySessionViewSet,
    LegalEntityViewSet,
    LocationViewSet,
    OneCExchangeLogViewSet,
    InventoryAIAnalyzeAPIView,
    OneCExportAPIView,
    OneCImportAPIView,
    TransferViewSet,
    WriteOffActViewSet,
)

router = DefaultRouter()
router.register("legal-entities", LegalEntityViewSet, basename="legal-entity")
router.register("locations", LocationViewSet, basename="location")
router.register("asset-categories", AssetCategoryViewSet, basename="asset-category")
router.register("employees", EmployeeViewSet, basename="employee")
router.register("assets", AssetViewSet, basename="asset")
router.register("inventory-sessions", InventorySessionViewSet, basename="inventory-session")
router.register("inventory-items", InventoryItemViewSet, basename="inventory-item")
router.register("transfers", TransferViewSet, basename="transfer")
router.register("write-off-acts", WriteOffActViewSet, basename="write-off-act")
router.register("integration-logs", OneCExchangeLogViewSet, basename="integration-log")

urlpatterns = [
    path("", include(router.urls)),
    path("integrations/1c/import/", OneCImportAPIView.as_view(), name="onec-import"),
    path("integrations/1c/export/", OneCExportAPIView.as_view(), name="onec-export"),
    path("inventory-items/<int:item_id>/ai-analyze/", InventoryAIAnalyzeAPIView.as_view(), name="inventory-ai-analyze"),
]
