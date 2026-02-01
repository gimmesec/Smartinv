from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WriteOffViewSet

router = DefaultRouter()
router.register(r'writeoffs', WriteOffViewSet, basename='writeoff')

urlpatterns = [
    path('', include(router.urls)),
]
