from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import (
    RegisterSerializer,
    RepRegisterSerializer,
    StudentTokenObtainPairSerializer,
    UserSerializer,
)


class StudentTokenObtainPairView(TokenObtainPairView):
    """Login by student_id instead of username."""

    serializer_class = StudentTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset           = User.objects.all()
    serializer_class   = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class RepRegisterView(generics.CreateAPIView):
    queryset           = User.objects.all()
    serializer_class   = RepRegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class   = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.select_related("department")

    def get_object(self):
        return self.request.user
