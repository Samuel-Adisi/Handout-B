import hmac
import hashlib
import requests
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, generics

from .models import Payment
from .serializers import PaymentSerializer, PaymentStatusSerializer
from .paystack import initiate_momo_payment, verify_payment
from handouts.models import Handout


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        payment = serializer.save()

        try:
            ps_response = initiate_momo_payment(payment)
            ps_status   = ps_response.get("status")       # "success" or "error"
            ps_message  = ps_response.get("message", "")
            ps_data     = ps_response.get("data", {})
            next_step   = ps_data.get("status")           # "send_otp", "success", "pay_offline"

            if ps_status == "success" or ps_message == "Charge attempted":
                return Response({
                "message": "MoMo payment initiated.",
                "reference": payment.reference,
                "payment_id": str(payment.id),
                "next_step": next_step or "send_otp",
             }, status=status.HTTP_201_CREATED)
            else:
                payment.status = "failed"
                payment.save()
                return Response({
                    "error": ps_message or "Payment initiation failed."
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            payment.status = "failed"
            payment.save()
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)




class SubmitOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        otp       = request.data.get("otp")
        reference = request.data.get("reference")

        if not otp or not reference:
            return Response(
                {"error": "OTP and reference are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        url     = "https://api.paystack.co/charge/submit_otp"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type":  "application/json",
        }
        payload = {"otp": otp, "reference": reference}

        try:
            response  = requests.post(url, json=payload, headers=headers)
            data      = response.json()
            ps_data   = data.get("data", {})
            ps_status = ps_data.get("status")

            print("SUBMIT OTP STATUS:", response.status_code)
            print("SUBMIT OTP RESPONSE:", data)

            if ps_status in ["success", None]:
                return Response(
                    {"message": "Payment approved successfully."},
                    status=status.HTTP_200_OK
                )
                

            elif ps_status == "pay_offline":
                return Response(
                    {"message": "Please dial *170# to approve the payment."},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"message": "OTP submitted. Waiting for confirmation.", "status": ps_status},
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class PaystackWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Verify Paystack signature
        paystack_sig = request.headers.get("x-paystack-signature", "")
        computed     = hmac.new(
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