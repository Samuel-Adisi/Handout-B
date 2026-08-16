from django.urls import path

from .views import CourseDetailView, CourseListCreateView

urlpatterns = [
    path("",          CourseListCreateView.as_view(), name="course-list"),
    path("<int:pk>/", CourseDetailView.as_view(),     name="course-detail"),
]
