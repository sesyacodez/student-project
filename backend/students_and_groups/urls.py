from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import GroupViewSet, StudentViewSet

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")
router.register("groups", GroupViewSet, basename="group")

urlpatterns = router.urls