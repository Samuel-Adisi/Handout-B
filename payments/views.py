import hashlib
import hmac
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django.utils import timezone
from .models import Payment
from .serializers import PaymentSerializer, PaymentStatusSerializer
from .paystack import initiate_momo_payment

class InitiatePaymentView(generics.CreateAPIView):
    serializer_class   = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        handout = serializer.validated_data.get("handout")
        payment = serializer.save(amount=handout.price)
        initiate_momo_payment(payment)

class PaystackWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        signature = request.headers.get("x-paystack-signature", "")
        computed  = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
            request.body,
            hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(computed, signature):
            return Response({"detail": "Invalid signature."}, status=400)

        event = request.data.get("event")
        data  = request.data.get("data", {})

        if event == "charge.success":
            reference = data.get("reference")
            try:
                payment = Payment.objects.select_related(
                    "student", "handout", "handout__course"
                ).get(reference=reference)
            except Payment.DoesNotExist:
                return Response({"detail": "Payment not found."}, status=404)

            if payment.status != "successful":
                payment.status       = "successful"
                payment.confirmed_at = timezone.now()
                payment.handout.stock -= 1
                payment.handout.save()
                payment.save()

                from notifications.tasks import send_receipt
                send_receipt.delay(str(payment.id))

        return Response({"detail": "Webhook received."}, status=200)

class PaymentStatusView(generics.RetrieveAPIView):
    serializer_class   = PaymentStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.select_related(
            "student", "handout", "handout__course"
        ).filter(student=self.request.user)

class MyPaymentsView(generics.ListAPIView):
    serializer_class   = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.select_related(
            "student", "handout", "handout__course"
        ).filter(student=self.request.user).order_by("-created_at")

class RepPaymentsView(generics.ListAPIView):
    serializer_class   = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role not in ["rep", "admin"]:
            return Payment.objects.none()
        return Payment.objects.select_related(
            "student", "handout", "handout__course"
        ).filter(
            handout__course__rep=self.request.user
        ).order_by("-created_at")