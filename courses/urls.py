from django.urls import path
from .views import CourseListCreateView, CourseDetailView

urlpatterns = [
    path("",       CourseListCreateView.as_view()),
    path("<int:pk>/", CourseDetailView.as_view()),
]