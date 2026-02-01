from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ToolNameViewSet, ToolViewSet, ToolTransferHistoryViewSet

router = DefaultRouter()
router.register(r'tool-names', ToolNameViewSet, basename='tool-name')
router.register(r'tools', ToolViewSet, basename='tool')
router.register(r'tool-transfer-history', ToolTransferHistoryViewSet, basename='tool-transfer-history')

urlpatterns = [
    path('', include(router.urls)),
]
