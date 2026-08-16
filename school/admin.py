from django.contrib import admin

from .models import School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display  = ("name", "region", "address", "is_active", "created_at")
    list_filter   = ("region", "is_active")
    search_fields = ("name", "region", "address")
