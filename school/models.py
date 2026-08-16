from django.db import models
from accounts.models import User

# Create your models here.

class School(models.Model):
    name       = models.CharField(max_length=100)
    region     = models.CharField(max_length=100)
    address    = models.CharField(max_length=100)
    # SET_NULL, not CASCADE: removing the staff member who registered a school
    # must not delete the school.
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="schools_created",
        null=True,
        blank=True,
    )
    is_active  = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {self.address}"
