from django.contrib import admin

from .models import Handout


@admin.register(Handout)
class HandoutAdmin(admin.ModelAdmin):
    list_display  = ("title", "course", "department", "price", "stock", "is_active", "created_at")
    list_filter   = ("is_active", "department", "course")
    search_fields = ("title", "course__code", "course__name")
    autocomplete_fields = ("course", "department")
