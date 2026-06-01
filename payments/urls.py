from django.urls import path
from .views import (
    InitiatePaymentView,
    SubmitOTPView,
    PaymentStatusView,
    PaystackWebhookView,
    MyPaymentsView,
    RepPaymentsView,
)

urlpatterns = [
    path("initiate/",          InitiatePaymentView.as_view(),  name="payment-initiate"),
    path("submit-otp/",        SubmitOTPView.as_view(),         name="submit-otp"),
    path("my/",                MyPaymentsView.as_view(),        name="my-payments"),
    path("rep/",               RepPaymentsView.as_view(),       name="rep-payments"),
    path("<uuid:pk>/status/",  PaymentStatusView.as_view(),     name="payment-status"),
    path("webhook/paystack/",  PaystackWebhookView.as_view(),   name="paystack-webhook"),
]