from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from department.models import Department

class UserManager(BaseUserManager):
    def create_user(self, student_id, password=None, **extra_fields):
        if not student_id:
            raise ValueError("Student ID is required")
        user = self.model(student_id=student_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, student_id, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(student_id, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("rep",     "Course Rep"),
        ("admin",   "Admin"),
    ]
    student_id  = models.CharField(max_length=20, unique=True)
    name        = models.CharField(max_length=150)
    phone       = models.CharField(max_length=15)
    department  = models.ForeignKey(Department, on_delete=models.CASCADE)
    role        = models.CharField(max_length=10, choices=ROLE_CHOICES, default="student")
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD  = "student_id"
    REQUIRED_FIELDS = ["name", "phone"]

    def __str__(self):
        return f"{self.name} ({self.student_id})"