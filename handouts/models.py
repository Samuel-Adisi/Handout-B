from django.db import models
from courses.models import Course
from department.models import Department



class Handout(models.Model):
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="handouts")
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Defaults to the owning rep's department in Handout.save() when not given.
    department  = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="handouts",
        null=True,
        blank=True,
    )
    price       = models.DecimalField(max_digits=8, decimal_places=2)
    stock       = models.PositiveIntegerField(default=0)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.course.code}"

    def save(self, *args, **kwargs):
        if self.department_id is None and self.course_id is not None:
            self.department_id = self.course.rep.department_id
        super().save(*args, **kwargs)

    def has_stock(self):
        # `stock` is non-null now, but stay defensive: legacy rows may hold NULL
        # until the backfill migration has run everywhere.
        return (self.stock or 0) > 0