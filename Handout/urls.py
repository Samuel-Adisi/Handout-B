from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/",      admin.site.urls),
    path("api/accounts/",     include("accounts.urls")),
    path("api/courses/",  include("courses.urls")),
    path("api/handouts/", include("handouts.urls")),
    path("api/payments/", include("payments.urls")),
]