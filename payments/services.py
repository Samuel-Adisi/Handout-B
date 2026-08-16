"""Single place where a Payment changes state.

Confirmation used to be duplicated between the status poller and the MTN
callback, neither of which took a lock. Two concurrent requests could both
observe a pending payment, both mark it successful and both decrement stock,
selling one copy twice over.
"""

import logging

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from handouts.models import Handout

from .models import Payment

logger = logging.getLogger(__name__)

SUCCESS_STATUSES = {"SUCCESSFUL", "SUCCESS", "COMPLETED"}
FAILURE_STATUSES = {"FAILED", "CANCELLED", "CANCELED", "REJECTED", "TIMEOUT"}


def available_stock(handout) -> int:
    """Units that may still be sold.

    Stock is only decremented once a payment succeeds, so pending attempts
    have to be subtracted as well — otherwise ten students can each pass an
    `stock > 0` check against the same single copy and all be charged.
    """
    pending = Payment.objects.filter(
        handout=handout, status__in=Payment.OPEN_STATUSES
    ).count()
    return max((handout.stock or 0) - pending, 0)


@transaction.atomic
def confirm_payment(payment_id) -> Payment:
    """Mark a payment successful and consume one unit of stock.

    Idempotent: calling it twice for the same payment decrements stock once.
    """
    payment = (
        Payment.objects
        .select_for_update()
        .select_related("handout")
        .get(pk=payment_id)
    )

    if payment.status == "successful":
        return payment

    payment.status       = "successful"
    payment.confirmed_at = timezone.now()
    payment.save(update_fields=["status", "confirmed_at"])

    # Conditional UPDATE ... WHERE stock > 0, so the counter can never be
    # driven negative by a race, and F() avoids a read-modify-write.
    decremented = Handout.objects.filter(
        pk=payment.handout_id, stock__gt=0
    ).update(stock=F("stock") - 1)

    if not decremented:
        logger.error(
            "Payment %s confirmed but handout %s had no stock left; oversold.",
            payment.reference,
            payment.handout_id,
        )

    transaction.on_commit(lambda: _queue_receipt(payment.pk))
    return payment


@transaction.atomic
def fail_payment(payment_id, status="failed") -> Payment:
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    # Never walk a settled payment back to a failure state.
    if payment.status in Payment.FINAL_STATUSES:
        return payment

    payment.status = status
    payment.save(update_fields=["status"])
    return payment


def apply_momo_status(payment, momo_status: str) -> Payment:
    """Translate an MTN status string into a local state transition."""
    momo_status = str(momo_status or "").upper()

    if momo_status in SUCCESS_STATUSES:
        return confirm_payment(payment.pk)
    if momo_status in FAILURE_STATUSES:
        return fail_payment(payment.pk)

    # PENDING or anything unrecognised: leave it alone and keep polling.
    return payment


def _queue_receipt(payment_id) -> None:
    from notifications.tasks import send_receipt

    try:
        send_receipt.delay(str(payment_id))
    except Exception:  # broker unreachable
        # A receipt is not worth failing a confirmed payment over.
        logger.exception("Could not queue receipt for payment %s", payment_id)
