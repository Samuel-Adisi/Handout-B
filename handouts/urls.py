from django.urls import path

from .views import HandoutDetailView, HandoutListCreateView

urlpatterns = [
    path("",          HandoutListCreateView.as_view(), name="handout-list"),
    path("<int:pk>/", HandoutDetailView.as_view(),     name="handout-detail"),
]
