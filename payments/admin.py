from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display    = ("reference", "student", "handout", "amount", "status", "created_at", "confirmed_at")
    list_filter     = ("status", "momo_provider", "created_at")
    search_fields   = ("reference", "student__student_id", "student__name", "handout__title")
    date_hierarchy  = "created_at"
    # Financial records are read-only in the admin: status changes must go
    # through payments.services so stock stays consistent.
    readonly_fields = tuple(f.name for f in Payment._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
