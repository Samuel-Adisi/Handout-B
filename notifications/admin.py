from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ("type", "channel", "recipient", "sent", "sent_at", "created_at")
    list_filter   = ("type", "channel", "sent")
    search_fields = ("recipient__name", "recipient__student_id", "message")
    readonly_fields = ("created_at", "sent_at")
