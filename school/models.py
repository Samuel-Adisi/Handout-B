from django.db import models
from accounts.models import User

# Create your models here.

class School(models.Model):
    name = models.CharField(max_length=100, blank=False,null=False)
    region = models.CharField(max_length=100, blank=False, null=False)
    address = models.CharField(max_length=100, blank=False, null=False)
    created_by = models.ForeignKey(User , on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return F"{self.name} - {self.address}"
