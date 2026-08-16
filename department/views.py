from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Department
from .serializers import DepartmentSerializer


class DepartmentListView(generics.ListAPIView):
    """Public list of active departments.

    Registration requires a department id, so the signup form has to be able
    to read this list before the user has an account. Only active departments
    are exposed, and the payload carries no sensitive data.
    """

    serializer_class   = DepartmentSerializer
    permission_classes = [AllowAny]
    pagination_class   = None

    def get_queryset(self):
        return Department.objects.filter(is_active=True)
