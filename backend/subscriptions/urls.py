from rest_framework.routers import DefaultRouter

from .views import PricingTierViewSet, StudentSubscriptionViewSet, SubscriptionPlanViewSet

router = DefaultRouter()
router.register("subscription-plans", SubscriptionPlanViewSet, basename="subscription-plan")
router.register("student-subscriptions", StudentSubscriptionViewSet, basename="student-subscription")
router.register("pricing-tiers", PricingTierViewSet, basename="pricing-tier")

urlpatterns = router.urls