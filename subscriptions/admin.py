from django.contrib import admin

from .models import PricingTier, StudentSubscription, SubscriptionPlan


class PricingTierInline(admin.TabularInline):
    model = PricingTier
    extra = 1


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "type", "status")
    list_filter = ("type", "status", "branch")
    search_fields = ("name",)
    filter_horizontal = ("subjects",)
    inlines = [PricingTierInline]


@admin.register(PricingTier)
class PricingTierAdmin(admin.ModelAdmin):
    list_display = ("subscription_plan", "lessons_per_month", "price_per_lesson")
    list_filter = ("subscription_plan",)


@admin.register(StudentSubscription)
class StudentSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("student", "subscription_plan", "subject", "start_date")
    list_filter = ("subscription_plan", "subject", "start_date")
    search_fields = ("student__first_name", "student__last_name", "subject__name")
