from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError

from accounts.permissions import IsOwningRepOrAdmin, IsRepOrAdmin, is_admin

from .models import Handout
from .serializers import HandoutSerializer


class HandoutListCreateView(generics.ListCreateAPIView):
    serializer_class   = HandoutSerializer
    permission_classes = [permissions.IsAuthenticated, IsRepOrAdmin]

    def get_queryset(self):
        user     = self.request.user
        queryset = Handout.objects.select_related(
            "course", "course__rep", "department"
        ).filter(is_active=True)

        if user.role == "rep":
            queryset = queryset.filter(course__rep=user)

        course = self.request.query_params.get("course")
        if course:
            queryset = queryset.filter(course_id=course)
        return queryset

    def perform_create(self, serializer):
        user   = self.request.user
        course = serializer.validated_data.get("course")
        # A rep may only publish handouts under their own courses.
        if not is_admin(user) and course.rep_id != user.id:
            raise ValidationError(
                {"course_id": "You can only add handouts to your own courses."}
            )
        serializer.save()


class HandoutDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = HandoutSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwningRepOrAdmin]
    queryset           = Handout.objects.select_related(
        "course", "course__rep", "department"
    )
    owner_field        = "course.rep"
