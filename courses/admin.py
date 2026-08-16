from django.contrib import admin

from .models import Course


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display  = ("code", "name", "rep", "is_active", "created_at")
    list_filter   = ("is_active", "rep__department")
    search_fields = ("code", "name", "rep__name", "rep__student_id")
    autocomplete_fields = ("rep",)
