from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
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
    # Rate limited: the login endpoint is otherwise an unmetered oracle for
    # brute-forcing passwords against known student IDs.
    throttle_scope   = "login"


class RegisterView(generics.CreateAPIView):
    queryset           = User.objects.all()
    serializer_class   = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope     = "register"


class RepRegisterView(generics.CreateAPIView):
    queryset           = User.objects.all()
    serializer_class   = RepRegisterSerializer
    permission_classes = [permissions.AllowAny]
    # Tighter than student signup: this endpoint guesses at an invite code.
    throttle_scope     = "register"


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class   = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.select_related("department")

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    """Blacklist a refresh token so it cannot be used again.

    Access tokens are stateless and stay valid until they expire, which is why
    their lifetime is now measured in minutes rather than a day.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.data.get("refresh")
        if not token:
            return Response(
                {"refresh": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(token).blacklist()
        except TokenError:
            return Response(
                {"refresh": "Token is invalid or already blacklisted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)
