from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError

from accounts.permissions import IsOwningRepOrAdmin, IsRepOrAdmin, is_admin

from .models import Course
from .serializers import CourseSerializer


class CourseListCreateView(generics.ListCreateAPIView):
    serializer_class   = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsRepOrAdmin]

    def get_queryset(self):
        user = self.request.user
        qs   = Course.objects.select_related("rep", "rep__department")
        if user.role == "rep":
            return qs.filter(rep=user, is_active=True)
        return qs.filter(is_active=True)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == "rep":
            # A rep always owns what they create; rep_id from the body is ignored.
            serializer.save(rep=user)
            return
        if not serializer.validated_data.get("rep"):
            raise ValidationError(
                {"rep_id": "Admins must nominate the course rep."}
            )
        serializer.save()


class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwningRepOrAdmin]
    queryset           = Course.objects.select_related("rep", "rep__department")
    owner_field        = "rep"

    def perform_update(self, serializer):
        # Only an admin may hand a course to a different rep.
        if not is_admin(self.request.user):
            serializer.validated_data.pop("rep", None)
        serializer.save()
