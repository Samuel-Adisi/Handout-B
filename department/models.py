from django.db import models

# Create your models here.



class Department(models.Model):
    DEPARTMENT_TYPE = [("hnd", "HND"),
                       ("btech", "BTECH")
                       ]
    name = models.CharField(max_length=100, blank=False,null=False)
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    department_type = models. CharField(choices=DEPARTMENT_TYPE, blank=False)
    created_by = models.ForeignKey(User , on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    
    def __str__(self):
        return F"{self.name}"
