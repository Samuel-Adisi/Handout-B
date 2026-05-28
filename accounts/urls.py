from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, MeView,RepRegisterView,clerk_auth
from .serializers import StudentTokenObtainPairView  # 
from django.http import JsonResponse

def ping(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path("register/", RegisterView.as_view(),       name="register"),
    path("register/rep/", RepRegisterView.as_view(), name="register-rep"),
    path("login/",        StudentTokenObtainPairView.as_view(), name="login"),
    path("refresh/",  TokenRefreshView.as_view(),    name="token-refresh"),
    path("me/",       MeView.as_view(),              name="me"),
    path("ping/", ping),
    path('clerk-auth/', clerk_auth, name='clerk-auth'),
]



