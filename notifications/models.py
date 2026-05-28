from django.db import models
from accounts.models import User
from payments.models import Payment


class Notification(models.Model):
    TYPE_CHOICES = [
        ("receipt",  "Payment Receipt"),
        ("reminder", "Payment Reminder"),
        ("alert",    "Stock Alert"),
    ]

    CHANNEL_CHOICES = [
        ("sms",   "SMS"),
        ("email", "Email"),
    ]

    recipient   = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    payment     = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
    type        = models.CharField(max_length=10, choices=TYPE_CHOICES)
    channel     = models.CharField(max_length=5, choices=CHANNEL_CHOICES)
    message     = models.TextField()
    sent        = models.BooleanField(default=False)
    sent_at     = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} → {self.recipient.name} [{self.channel}]"