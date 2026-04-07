from django.contrib import admin

from .models import Branch, Subject


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
	list_display = ("name", "city", "status")
	list_filter = ("status", "city")
	search_fields = ("name", "city")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
	list_display = ("name", "branch", "status")
	list_filter = ("status", "branch")
	search_fields = ("name",)
