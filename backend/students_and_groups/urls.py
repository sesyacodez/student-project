from rest_framework.routers import DefaultRouter

from .views import GroupViewSet, StudentViewSet

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")
router.register("groups", GroupViewSet, basename="group")

urlpatterns = router.urls