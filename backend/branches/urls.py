from rest_framework.routers import DefaultRouter

from .views import BranchViewSet, SubjectViewSet

router = DefaultRouter()
router.register("branches", BranchViewSet, basename="branch")
router.register("subjects", SubjectViewSet, basename="subject")

urlpatterns = router.urls