from django.contrib import admin

from .models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ("name", "department_type", "is_active", "created_at")
    list_filter   = ("department_type", "is_active")
    search_fields = ("name",)
    list_editable = ("is_active",)
