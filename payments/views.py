import logging

from django.conf import settings
from django.utils.crypto import constant_time_compare
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import is_admin

from .models import Payment
from .momo import MoMoError, initiate_momo_payment, verify_payment
from .serializers import PaymentSerializer, PaymentStatusSerializer
from .services import apply_momo_status

logger = logging.getLogger(__name__)


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope     = "payment"

    def post(self, request):
        serializer = PaymentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()

        try:
            initiate_momo_payment(payment)
        except MoMoError as exc:
            payment.status = "failed"
            payment.save(update_fields=["status"])
            logger.warning("Payment %s could not be initiated: %s", payment.reference, exc)
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "message":    "MoMo payment initiated. Check your phone to approve.",
                "reference":  str(payment.reference),
                "payment_id": str(payment.id),
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentStatusView(generics.RetrieveAPIView):
    """GET /api/payments/<reference>/status/ — reconciles with MTN if pending."""

    permission_classes = [IsAuthenticated]
    serializer_class   = PaymentStatusSerializer

    def get_object(self):
        try:
            payment = Payment.objects.get(
                reference=self.kwargs["pk"], student=self.request.user
            )
        except Payment.DoesNotExist:
            raise NotFound("Payment not found.")

        if payment.status in Payment.FINAL_STATUSES:
            return payment

        try:
            result = verify_payment(str(payment.reference))
        except MoMoError as exc:
            # Upstream trouble is not the client's problem; report what we know.
            logger.info("Could not refresh %s: %s", payment.reference, exc)
            return payment

        payment = apply_momo_status(payment, result.get("status"))
        payment.refresh_from_db()
        return payment


class MoMoCallbackView(APIView):
    """POST /api/payments/callback/ — MTN's asynchronous result notification.

    The callback body is treated purely as a hint that something changed. The
    endpoint is public and unauthenticated, so believing its `status` field
    meant anyone could POST their own reference with status SUCCESSFUL and
    collect the handout without paying. Every notification is re-verified
    against MTN before any state changes.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope     = "callback"

    def post(self, request):
        expected = settings.MOMO_CALLBACK_TOKEN
        if expected and not constant_time_compare(
            request.headers.get("X-Callback-Token", ""), expected
        ):
            logger.warning("Rejected MoMo callback with a bad token.")
            return Response(status=status.HTTP_403_FORBIDDEN)

        reference = (
            request.data.get("correlatorId")
            or request.data.get("transactionId")
            or request.data.get("externalId")
        )
        if not reference:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(reference=reference)
        except Payment.DoesNotExist:
            # Acknowledge unknown references so MTN stops retrying, but say
            # nothing about whether the reference exists.
            return Response(status=status.HTTP_200_OK)

        if payment.status in Payment.FINAL_STATUSES:
            return Response(status=status.HTTP_200_OK)

        try:
            result = verify_payment(str(payment.reference))
        except MoMoError as exc:
            logger.warning("Callback for %s could not be verified: %s", reference, exc)
            # 503 asks MTN to retry rather than dropping the notification.
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        apply_momo_status(payment, result.get("status"))
        return Response(status=status.HTTP_200_OK)


class MyPaymentsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(student=self.request.user).select_related(
            "student", "handout", "handout__course", "handout__course__rep"
        )


class RepPaymentsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = PaymentSerializer

    def get_queryset(self):
        queryset = Payment.objects.select_related(
            "student", "handout", "handout__course", "handout__course__rep"
        )
        if is_admin(self.request.user):
            return queryset
        return queryset.filter(handout__course__rep=self.request.user)
