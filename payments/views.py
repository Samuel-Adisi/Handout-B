import hashlib
import hmac
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, generics

from .models import Payment
from .serializers import PaymentSerializer, PaymentStatusSerializer
from .paystack import initiate_momo_payment, verify_payment
 # updated import
from handouts.models import Handout


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        payment = serializer.save()

        try:
            flw_response = initiate_momo_payment(payment)
            flw_status   = flw_response.get("status")      # "success" or "error"
            flw_message  = flw_response.get("message", "")

            if flw_status == "success":
                return Response({
                    "message": "MoMo prompt sent. Approve on your phone or via SMS.",
                    "reference": payment.reference,
                    "flw_status": flw_status,
                    "flw_message": flw_message,
                }, status=status.HTTP_201_CREATED)
            else:
                payment.status = "failed"
                payment.save()
                return Response({
                    "error": flw_message or "Payment initiation failed."
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            payment.status = "failed"
            payment.save()
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class  FlutterwaveWebhookView(APIView):  # keep name or rename to FlutterwaveWebhookView
    permission_classes = [AllowAny]

    def post(self, request):
        # Verify Flutterwave signature
        paystack_sig = request.headers.get("x-paystack-signature", "")
        import hmac, hashlib
        computed = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
            request.body,
            hashlib.sha512,
        ).hexdigest()

        if paystack_sig != computed:
            return Response({"error": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

        payload = request.data
        event   = payload.get("event")

        if event == "charge.success":
            data      = payload.get("data", {})
            reference = data.get("reference")
            currency  = data.get("currency")
            amount    = data.get("amount")  # in pesewas

            try:
                payment = Payment.objects.get(reference=reference)
            except Payment.DoesNotExist:
                return Response(status=status.HTTP_200_OK)

            # Double-verify with Paystack API
            verify_resp = verify_payment(reference)
            verified    = verify_resp.get("data", {})

            if (
                verified.get("status") == "success"
                and verified.get("currency") == "GHS"
                and int(verified.get("amount", 0)) >= int(float(payment.amount) * 100)
            ):
                payment.status       = "successful"
                payment.confirmed_at = timezone.now()
                payment.save()

                handout = payment.handout
                if handout.stock > 0:
                    handout.stock -= 1
                    handout.save()
            else:
                payment.status = "failed"
                payment.save()

        return Response(status=status.HTTP_200_OK)


class PaymentStatusView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = PaymentStatusSerializer

    def get_queryset(self):
        return Payment.objects.filter(student=self.request.user)


class MyPaymentsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(student=self.request.user).order_by("-created_at")


class RepPaymentsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(
            handout__rep=self.request.user
        ).order_by("-created_at")