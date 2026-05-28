from rest_framework import generics, permissions
from .models import Course
from .serializers import CourseSerializer

class IsRepOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True  # students can view courses
        return request.user.role in ["rep", "admin"]  # only rep/admin can create/edit/delete


class CourseListCreateView(generics.ListCreateAPIView):
    serializer_class   = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsRepOrAdmin]  # ← add IsRepOrAdmin

    def get_queryset(self):
        user = self.request.user
        if user.role == "rep":
            return Course.objects.filter(rep=user, is_active=True)
        return Course.objects.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(rep=self.request.user)


class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsRepOrAdmin]
    queryset           = Course.objects.all()