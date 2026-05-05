from django.contrib import admin
from .models import User

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('phone', 'first_name', 'last_name', 'role', 'branch', 'is_active')
    list_filter = ('role', 'branch', 'is_active')
    search_fields = ('phone', 'first_name', 'last_name')