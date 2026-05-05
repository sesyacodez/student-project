from rest_framework.routers import DefaultRouter

from .api import SubjectViewSet

router = DefaultRouter()
router.register("subjects", SubjectViewSet, basename="subject")

urlpatterns = router.urls