from celery import shared_task
from django.utils import timezone
from datetime import timedelta

@shared_task
def expire_pending_payments():
    from .models import Payment
    expiry_time = timezone.now() - timedelta(minutes=30)
    expired = Payment.objects.filter(
        status="pending",
        created_at__lt=expiry_time
    )
    count = expired.update(status="expired")
    return f"{count} payments expired"