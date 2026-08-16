from django.db import models


# Create your models here.



class Department(models.Model):
    DEPARTMENT_TYPE = [
        ("hnd", "HND"),
        ("btech", "BTECH"),
    ]

    name            = models.CharField(max_length=100)
    department_type = models.CharField(max_length=10, choices=DEPARTMENT_TYPE)
    is_active       = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ["name"]
        constraints         = [
            models.UniqueConstraint(
                fields=["name", "department_type"],
                name="unique_department_name_per_type",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_department_type_display()})"
