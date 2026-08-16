from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class UserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model  = User
        fields = ("student_id", "name", "phone", "department", "role")


class UserEditForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Uses Django's UserAdmin so passwords are hashed, not stored raw."""

    add_form = UserCreateForm
    form     = UserEditForm
    model    = User

    ordering     = ("student_id",)
    list_display = ("student_id", "name", "phone", "role", "department", "is_active", "created_at")
    list_filter  = ("role", "is_active", "is_staff", "department")
    search_fields = ("student_id", "name", "phone")
    readonly_fields = ("created_at", "last_login")

    fieldsets = (
        (None,           {"fields": ("student_id", "password")}),
        ("Profile",      {"fields": ("name", "phone", "department")}),
        ("Permissions",  {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Timestamps",   {"fields": ("last_login", "created_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("student_id", "name", "phone", "department", "role", "password1", "password2"),
        }),
    )
