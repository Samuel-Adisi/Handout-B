import requests
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, generics
from rest_framework.exceptions import NotFound

from .models import Payment
from .serializers import PaymentSerializer, PaymentStatusSerializer
from .momo import initiate_momo_payment, verify_payment


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        payment = serializer.save()
        

        try:
            initiate_momo_payment(payment)
            return Response(
                {
                    "message": "MoMo payment initiated. Check your phone to approve.",
                    "reference": str(payment.reference),
                    "payment_id": str(payment.id),
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            payment.status = "failed"
            payment.save(update_fields=["status"])
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)



class PaymentStatusView(generics.RetrieveAPIView):
    """
    GET /payments/<reference>/status/
    Polls MTN and syncs the local Payment status.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentStatusSerializer

    def get_object(self):
        reference = self.kwargs.get("pk")
        try:
            payment = Payment.objects.get(reference=reference, student=self.request.user)
        except Payment.DoesNotExist:
            raise NotFound("Payment not found.")

        # Already resolved — skip the MTN call
        if payment.status in ("successful", "failed", "expired"):
            return payment

        try:
            result     = verify_payment(str(payment.reference))
            mtn_status = result.get("status", "PENDING").upper()

            if mtn_status == "SUCCESSFUL":
                payment.status       = "successful"
                payment.confirmed_at = timezone.now()
                payment.save(update_fields=["status", "confirmed_at"])

                # Decrement stock
                handout = payment.handout
                if handout.stock > 0:
                    handout.stock -= 1
                    handout.save(update_fields=["stock"])

            elif mtn_status in ("FAILED", "CANCELLED"):
                payment.status = "failed"
                payment.save(update_fields=["status"])

            # PENDING → leave as-is, frontend keeps polling

        except Exception as e:
            print("MTN verify error:", e)

        return payment


class MoMoCallbackView(APIView):
    """
    POST /api/payments/callback/
    MTN posts the final transaction result here (matches portal callback URL).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        data       = request.data
        mtn_status = str(data.get("status", "")).upper()

        # MTN sends correlatorId or transactionId as the reference
        reference = (
            data.get("correlatorId")
            or data.get("transactionId")
            or data.get("externalId")
        )

        print("MTN CALLBACK DATA:", data)

        if not reference:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(reference=reference)
        except Payment.DoesNotExist:
            return Response(status=status.HTTP_200_OK)  # ack, ignore unknown refs

        if mtn_status == "SUCCESSFUL" and payment.status != "successful":
            payment.status       = "successful"
            payment.confirmed_at = timezone.now()
            payment.save(update_fields=["status", "confirmed_at"])

            handout = payment.handout
            if handout.stock > 0:
                handout.stock -= 1
                handout.save(update_fields=["stock"])

        elif mtn_status in ("FAILED", "CANCELLED") and payment.status == "pending":
            payment.status = "failed"
            payment.save(update_fields=["status"])

        return Response(status=status.HTTP_200_OK)


class MyPaymentsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(student=self.request.user).order_by("-created_at")



class RepPaymentsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(
            handout__course__rep=self.request.user
        ).order_by("-created_at")