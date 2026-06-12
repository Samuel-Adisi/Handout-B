from django.urls import path
from .views import (
    InitiatePaymentView,
    PaymentStatusView,
    MoMoCallbackView,
    MyPaymentsView,
    RepPaymentsView,
)

urlpatterns = [
    path("initiate/",      InitiatePaymentView.as_view(), name="payment-initiate"),
    path("my/",            MyPaymentsView.as_view(),      name="my-payments"),
    path("rep/",           RepPaymentsView.as_view(),     name="rep-payments"),
    path("<str:pk>/status/", PaymentStatusView.as_view(), name="payment-status"),
    path("callback/",      MoMoCallbackView.as_view(),    name="momo-callback"),
    
]