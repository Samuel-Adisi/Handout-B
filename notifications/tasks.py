import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def _record(recipient, payment, message, sent):
    from .models import Notification

    Notification.objects.create(
        recipient=recipient,
        payment=payment,
        type="receipt",
        channel="sms",
        message=message,
        # Record what actually happened. Previously every notification was
        # written with sent=True even when the SMS gateway had refused it.
        sent=sent,
        sent_at=timezone.now() if sent else None,
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_receipt(self, payment_id):
    """SMS the student and their course rep once a payment is confirmed."""
    from payments.models import Payment

    from .utils import send_sms

    try:
        payment = Payment.objects.select_related(
            "student", "handout", "handout__course", "handout__course__rep"
        ).get(id=payment_id)
    except Payment.DoesNotExist:
        logger.warning("Receipt requested for unknown payment %s", payment_id)
        return "Payment not found"

    if payment.status != "successful":
        # Only confirmed payments get a receipt.
        return "Payment not confirmed"

    student = payment.student
    rep     = payment.handout.course.rep
    handout = payment.handout

    # confirmed_at is set in the same transaction as the status, but fall back
    # rather than raising AttributeError on None if that ever drifts.
    confirmed = (payment.confirmed_at or timezone.now()).strftime("%d %b %Y %H:%M")

    student_message = (
        f"Payment confirmed!\n"
        f"Handout: {handout.title}\n"
        f"Course:  {handout.course.code}\n"
        f"Amount:  GHS {payment.amount}\n"
        f"Ref:     {payment.reference}\n"
        f"Date:    {confirmed}"
    )

    rep_message = (
        f"New payment received!\n"
        f"Student: {student.name} ({student.student_id})\n"
        f"Handout: {handout.title}\n"
        f"Amount:  GHS {payment.amount}\n"
        f"Ref:     {payment.reference}\n"
        f"Date:    {confirmed}"
    )

    student_sent = send_sms(student.phone, student_message)
    _record(student, payment, student_message, student_sent)

    rep_sent = send_sms(rep.phone, rep_message)
    _record(rep, payment, rep_message, rep_sent)

    return f"Receipts sent for payment {payment_id}"
