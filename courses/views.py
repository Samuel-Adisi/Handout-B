from django.db.models import Count, Q
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError

from accounts.permissions import IsOwningRepOrAdmin, IsRepOrAdmin, is_admin

from .models import Course
from .serializers import CourseSerializer


class CourseScopeMixin:
    """Limits courses to what the caller is entitled to see."""

    def get_queryset(self):
        user     = self.request.user
        queryset = (
            Course.objects
            .select_related("rep", "rep__department")
            # Annotated so CourseSerializer.handout_count does not issue one
            # extra query per course in the list response.
            .annotate(
                active_handout_count=Count(
                    "handouts", filter=Q(handouts__is_active=True), distinct=True
                )
            )
        )

        if is_admin(user):
            return queryset
        if user.role == "rep":
            return queryset.filter(rep=user)
        if user.department_id is None:
            return queryset.none()
        return queryset.filter(rep__department_id=user.department_id)


class CourseListCreateView(CourseScopeMixin, generics.ListCreateAPIView):
    serializer_class   = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsRepOrAdmin]

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == "rep":
            # A rep always owns what they create; rep_id from the body is ignored.
            serializer.save(rep=user)
            return
        if not serializer.validated_data.get("rep"):
            raise ValidationError({"rep_id": "Admins must nominate the course rep."})
        serializer.save()


class CourseDetailView(CourseScopeMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwningRepOrAdmin]
    owner_field        = "rep"

    def perform_update(self, serializer):
        # Only an admin may hand a course to a different rep.
        if not is_admin(self.request.user):
            serializer.validated_data.pop("rep", None)
        serializer.save()
