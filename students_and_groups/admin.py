from django.contrib import admin

from .models import Group, GroupMembership, Student


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


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ("group", "student", "join_date", "leave_date")
    list_filter = ("group", "leave_date")
