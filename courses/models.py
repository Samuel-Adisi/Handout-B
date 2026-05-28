from django.db import models
from accounts.models import User


class Course(models.Model):
    rep         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="courses", limit_choices_to={"role": "rep"})
    name        = models.CharField(max_length=200)
    code        = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"