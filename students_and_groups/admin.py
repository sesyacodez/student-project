from django.contrib import admin

from .models import Group, GroupMembership, PricingTier, Student, StudentSubscription, SubscriptionPlan


class PricingTierInline(admin.TabularInline):
    model = PricingTier
    extra = 1


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "branch", "status")
    list_filter = ("status", "branch")
    search_fields = ("first_name", "last_name", "phone", "parent_name")


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "status")
    list_filter = ("status", "branch")
    search_fields = ("name",)
    filter_horizontal = ("students",)


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


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ("group", "student", "join_date", "leave_date")
    list_filter = ("group", "leave_date")
