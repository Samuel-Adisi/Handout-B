from django.urls import path
from .views import HandoutListCreateView, HandoutDetailView

urlpatterns = [
    path("",          HandoutListCreateView.as_view()),
    path("<int:pk>/", HandoutDetailView.as_view()),
]