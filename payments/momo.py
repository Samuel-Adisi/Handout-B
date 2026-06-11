import uuid
import base64
import requests
from django.conf import settings

MOMO_BASE_URL     = getattr(settings, "MOMO_BASE_URL",     "https://api.mtn.com")
MOMO_CURRENCY     = getattr(settings, "MOMO_CURRENCY",     "GHS")
MOMO_CALLBACK_URL = getattr(settings, "MOMO_CALLBACK_URL", "https://handout.pythonanywhere.com/api/payments/callback/")


def _get_access_token() -> str:
    """OAuth2 client_credentials flow using Consumer Key + Secret."""
    credentials = base64.b64encode(
        f"{settings.MOMO_CONSUMER_KEY}:{settings.MOMO_CONSUMER_SECRET}".encode()
    ).decode()

    resp = requests.post(
        f"{MOMO_BASE_URL}/v1/oauth/access_token",
        params={"grant_type": "client_credentials"},
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type":  "application/x-www-form-urlencoded",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _to_msisdn(phone: str) -> str:
    """Normalise to 233XXXXXXXXX (no + prefix)."""
    phone = phone.strip().replace(" ", "")
    if phone.startswith("+"):
        phone = phone[1:]
    elif phone.startswith("0"):
        phone = "233" + phone[1:]
    return phone


def initiate_momo_payment(payment) -> dict:
    """
    POST /v2/payments
    Sends a USSD push to the payer's handset.
    payment.reference must be a UUID4.
    """
    token       = _get_access_token()
    msisdn      = _to_msisdn(payment.momo_number)
    correlator  = str(payment.reference)   # UUID4 used as idempotency key

    payload = {
        "amount":             str(int(float(payment.amount))),
        "currency":           MOMO_CURRENCY,
        "customerInfo":       {"customerMsisdn": msisdn},
        "serviceCode":        "MP",           # MoMo Pay
        "paymentMethod":      "MoMo",
        "paymentDescription": f"Payment for {payment.handout.title}",
        "correlatorId":       correlator,
        "callbackUrl":        MOMO_CALLBACK_URL,
    }

    resp = requests.post(
        f"{MOMO_BASE_URL}/v2/payments",
        json=payload,
        headers={
            "Authorization":  f"Bearer {token}",
            "Content-Type":   "application/json",
            "transactionId":  correlator,    # idempotency header
        },
        timeout=15,
    )

    print("MTN MOMO STATUS:", resp.status_code)
    print("MTN MOMO BODY:",   resp.text)

    # 200 or 202 = request accepted, USSD push sent
    if resp.status_code not in (200, 202):
        resp.raise_for_status()

    return {"reference": correlator, "status": "pending"}


def verify_payment(reference: str) -> dict:
    """
    GET /v2/payments/{correlatorId}
    Returns status: PENDING | SUCCESSFUL | FAILED | CANCELLED
    """
    token = _get_access_token()

    resp = requests.get(
        f"{MOMO_BASE_URL}/v2/payments/{reference}",
        headers={
            "Authorization": f"Bearer {token}",
            "transactionId": reference,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()