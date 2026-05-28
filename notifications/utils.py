import requests
from django.conf import settings
from django.core.mail import send_mail


def send_sms(phone, message):
    url = "https://api.hubtel.com/v1/messages/send"

    params = {
        "clientsecret": settings.HUBTEL_CLIENT_SECRET,
        "clientid":     settings.HUBTEL_CLIENT_ID,
        "from":         settings.HUBTEL_SENDER_ID,
        "to":           phone,
        "content":      message,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"SMS failed: {e}")
        return False


def send_email(to_email, subject, message):
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False