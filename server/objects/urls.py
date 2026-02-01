from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConstructionObjectViewSet

router = DefaultRouter()
router.register(r'objects', ConstructionObjectViewSet, basename='object')

urlpatterns = [
    path('', include(router.urls)),
]
