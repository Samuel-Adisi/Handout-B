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
    OPEN_STATUSES  = ("pending",)
    FINAL_STATUSES = ("successful", "failed", "expired")

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # PROTECT, not CASCADE: deleting a student or a handout must not silently
    # erase the financial record of what they paid.
    student       = models.ForeignKey(User, on_delete=models.PROTECT, related_name="payments")
    handout       = models.ForeignKey(Handout, on_delete=models.PROTECT, related_name="payments")
    amount        = models.DecimalField(max_digits=8, decimal_places=2)
    momo_number   = models.CharField(max_length=15)
    momo_provider = models.CharField(max_length=5, choices=PROVIDER_CHOICES, default="mtn")
    reference     = models.CharField(max_length=100, unique=True, editable=False)
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending", db_index=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    confirmed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering    = ["-created_at"]
        constraints = [
            # Replaces unique_together(student, handout), which made a failed
            # attempt permanently block the student from retrying and forced
            # the serializer to delete payment history to work around it.
            # A student may retry as often as they like, but can only ever
            # hold one successful payment per handout.
            models.UniqueConstraint(
                fields=["student", "handout"],
                condition=models.Q(status="successful"),
                name="one_successful_payment_per_handout",
            )
        ]
        indexes = [
            models.Index(fields=["handout", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.student.name} → {self.handout.title} [{self.status}]"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = str(uuid.uuid4())
        super().save(*args, **kwargs)
