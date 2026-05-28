from celery import shared_task

@shared_task
def send_receipt(payment_id):
    from payments.models import Payment
    from .models import Notification
    from .utils import send_sms, send_email
    from django.utils import timezone

    try:
        payment = Payment.objects.select_related(
            "student", "handout", "handout__course", "handout__course__rep"
        ).get(id=payment_id)
    except Payment.DoesNotExist:
        return "Payment not found"

    student = payment.student
    rep     = payment.handout.course.rep
    handout = payment.handout

    student_message = (
        f"Payment confirmed!\n"
        f"Handout: {handout.title}\n"
        f"Course:  {handout.course.code}\n"
        f"Amount:  GHS {payment.amount}\n"
        f"Ref:     {payment.reference}\n"
        f"Date:    {payment.confirmed_at.strftime('%d %b %Y %H:%M')}"
    )

    rep_message = (
        f"New payment received!\n"
        f"Student: {student.name} ({student.student_id})\n"
        f"Handout: {handout.title}\n"
        f"Amount:  GHS {payment.amount}\n"
        f"Ref:     {payment.reference}\n"
        f"Date:    {payment.confirmed_at.strftime('%d %b %Y %H:%M')}"
    )

    now = timezone.now()

    # --- notify student via SMS ---
    send_sms(student.phone, student_message)
    Notification.objects.create(
        recipient=student,
        payment=payment,
        type="receipt",
        channel="sms",
        message=student_message,
        sent=True,
        sent_at=now,
    )

    # --- notify student via email if they have one ---
    if student.email:
        send_email(
            to=student.email,
            subject=f"Payment Receipt - {handout.title}",
            message=student_message
        )
        Notification.objects.create(
            recipient=student,
            payment=payment,
            type="receipt",
            channel="email",
            message=student_message,
            sent=True,
            sent_at=now,
        )

    # --- notify rep via SMS ---
    send_sms(rep.phone, rep_message)
    Notification.objects.create(
        recipient=rep,
        payment=payment,
        type="receipt",
        channel="sms",
        message=rep_message,
        sent=True,
        sent_at=now,
    )

    return f"Receipts sent for payment {payment_id}"