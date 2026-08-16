from django.urls import path

from .views import DepartmentListView

urlpatterns = [
    path("", DepartmentListView.as_view(), name="department-list"),
]
