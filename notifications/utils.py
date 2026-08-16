import logging

import requests
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

HUBTEL_URL = "https://sms.hubtel.com/v1/messages/send"
TIMEOUT = 10


def send_sms(phone, message) -> bool:
    if not (settings.HUBTEL_CLIENT_ID and settings.HUBTEL_CLIENT_SECRET):
        logger.warning("Hubtel is not configured; skipping SMS to %s", phone)
        return False

    params = {
        "clientsecret": settings.HUBTEL_CLIENT_SECRET,
        "clientid":     settings.HUBTEL_CLIENT_ID,
        "from":         settings.HUBTEL_SENDER_ID,
        "to":           phone,
        "content":      message,
    }

    try:
        # timeout: without one a hung Hubtel connection blocks a worker forever.
        response = requests.get(HUBTEL_URL, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        # Log the exception, not the response: params carry the client secret.
        logger.warning("SMS to %s failed: %s", phone, exc)
        return False


def send_email(to_email, subject, message) -> bool:
    if not to_email:
        return False

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except Exception as exc:
        logger.warning("Email to %s failed: %s", to_email, exc)
        return False
