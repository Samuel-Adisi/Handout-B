from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
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


@api_view(['POST'])
@permission_classes([AllowAny])
def clerk_auth(request):
    email = request.data.get('email')
    name = request.data.get('name', '')
    clerk_id = request.data.get('clerk_id')

    if not email:
        return Response({'error': 'Email required'}, status=400)

    # Get or create user by email
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'name': name,
            'role': 'student',  # default role for Google sign-in
            'username': email.split('@')[0],
        }
    )

    # Generate Django JWT tokens
    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'role': user.role,
        'name': user.name,
        'id': user.id,
    })
