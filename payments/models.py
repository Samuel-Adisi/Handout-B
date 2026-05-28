import uuid
from django.db import models
from accounts.models import User
from handouts.models import Handout

class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending",    "Pending"),
        ("successful", "Successful"),
        ("failed",     "Failed"),
        ("expired",    "Expired"),
    ]
    PROVIDER_CHOICES = [
        ("mtn",      "MTN Mobile Money"),
        ("vod",      "Vodafone Cash"),
        ("atl",      "AirtelTigo Money"),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    handout       = models.ForeignKey(Handout, on_delete=models.CASCADE, related_name="payments")
    amount        = models.DecimalField(max_digits=8, decimal_places=2)
    momo_number   = models.CharField(max_length=15)
    momo_provider = models.CharField(max_length=5, choices=PROVIDER_CHOICES, default="mtn")
    reference     = models.CharField(max_length=100, unique=True, blank=True)
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at    = models.DateTimeField(auto_now_add=True)
    confirmed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "handout")

    def __str__(self):
        return f"{self.student.name} → {self.handout.title} [{self.status}]"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"HO-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)