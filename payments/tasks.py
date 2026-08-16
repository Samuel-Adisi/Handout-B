import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# A MoMo prompt the payer never answers stays pending on MTN's side. Give the
# transaction time to settle before asking about it...
RECONCILE_AFTER = timedelta(minutes=30)
# ...and only give up once MTN has had a full day to report a result.
ABANDON_AFTER = timedelta(hours=24)
BATCH_SIZE = 200


@shared_task
def expire_pending_payments():
    """Reconcile stale pending payments against MTN, then expire the dead ones.

    The previous version blindly flipped every pending payment older than 30
    minutes to "expired" without asking MTN. A payment the student had in fact
    approved — just slowly — was written off while their money was gone.
    """
    from .models import Payment
    from .momo import MoMoError, verify_payment
    from .services import apply_momo_status, fail_payment

    now = timezone.now()
    stale = Payment.objects.filter(
        status="pending", created_at__lt=now - RECONCILE_AFTER
    ).order_by("created_at")[:BATCH_SIZE]

    confirmed = failed = expired = unresolved = 0

    for payment in stale:
        try:
            result = verify_payment(str(payment.reference))
        except MoMoError as exc:
            logger.info("Could not reconcile %s: %s", payment.reference, exc)
            # Only abandon it once MTN has had long enough to answer.
            if payment.created_at < now - ABANDON_AFTER:
                fail_payment(payment.pk, status="expired")
                expired += 1
            else:
                unresolved += 1
            continue

        updated = apply_momo_status(payment, result.get("status"))

        if updated.status == "successful":
            confirmed += 1
        elif updated.status == "failed":
            failed += 1
        elif payment.created_at < now - ABANDON_AFTER:
            # Still pending after a day: MTN is never going to settle it.
            fail_payment(payment.pk, status="expired")
            expired += 1
        else:
            unresolved += 1

    logger.info(
        "Reconciled pending payments: %s confirmed, %s failed, %s expired, %s still open",
        confirmed, failed, expired, unresolved,
    )
    return {
        "confirmed":  confirmed,
        "failed":     failed,
        "expired":    expired,
        "unresolved": unresolved,
    }
