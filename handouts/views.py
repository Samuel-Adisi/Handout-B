from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError

from accounts.permissions import IsOwningRepOrAdmin, IsRepOrAdmin, is_admin

from .models import Handout
from .serializers import HandoutSerializer


class HandoutScopeMixin:
    """Limits handouts to what the caller is entitled to see.

    Applied to the detail view as well as the list view, otherwise a student
    can read any other department's handout by guessing its id.
    """

    def get_queryset(self):
        user     = self.request.user
        queryset = Handout.objects.select_related(
            "course", "course__rep", "department"
        )

        if is_admin(user):
            return queryset
        if user.role == "rep":
            return queryset.filter(course__rep=user)
        # Students see their own department only. Fail closed: no department
        # means no handouts, rather than every department's.
        if user.department_id is None:
            return queryset.none()
        return queryset.filter(department_id=user.department_id)


class HandoutListCreateView(HandoutScopeMixin, generics.ListCreateAPIView):
    serializer_class   = HandoutSerializer
    permission_classes = [permissions.IsAuthenticated, IsRepOrAdmin]

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)

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


class HandoutDetailView(HandoutScopeMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = HandoutSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwningRepOrAdmin]
    owner_field        = "course.rep"
