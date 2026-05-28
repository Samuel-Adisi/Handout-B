from django.db import models
from courses.models import Course


class Handout(models.Model):
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="handouts")
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price       = models.DecimalField(max_digits=8, decimal_places=2)
    stock       = models.PositiveIntegerField(default=0)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.course.code}"

    def has_stock(self):
        return self.stock > 0