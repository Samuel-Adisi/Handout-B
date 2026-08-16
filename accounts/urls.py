from django.http import JsonResponse
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LogoutView,
    MeView,
    RegisterView,
    RepRegisterView,
    StudentTokenObtainPairView,
)


def ping(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("register/",     RegisterView.as_view(),              name="register"),
    path("register/rep/", RepRegisterView.as_view(),           name="register-rep"),
    path("login/",        StudentTokenObtainPairView.as_view(), name="login"),
    path("refresh/",      TokenRefreshView.as_view(),          name="token-refresh"),
    path("logout/",       LogoutView.as_view(),                name="logout"),
    path("me/",           MeView.as_view(),                    name="me"),
    path("ping/",         ping,                                name="ping"),
]
