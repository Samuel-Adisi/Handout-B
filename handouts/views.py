from rest_framework import generics, permissions
from .models import Handout
from .serializers import HandoutSerializer

class IsRepOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role in ["rep", "admin"]

class HandoutListCreateView(generics.ListCreateAPIView):
    serializer_class   = HandoutSerializer
    permission_classes = [permissions.IsAuthenticated, IsRepOrAdmin]

    def get_queryset(self):
        user     = self.request.user
        course   = self.request.query_params.get("course")
        queryset = Handout.objects.select_related("course").filter(is_active=True)  # ← fixed

        if user.role == "rep":
            queryset = queryset.filter(course__rep=user)
        if course:
            queryset = queryset.filter(course_id=course)
        return queryset

class HandoutDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = HandoutSerializer
    permission_classes = [permissions.IsAuthenticated, IsRepOrAdmin]
    queryset           = Handout.objects.select_related("course").all()  # ← fixed