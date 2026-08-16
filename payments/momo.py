"""Thin client for the MTN MoMo collections API."""

import base64
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TOKEN_TIMEOUT   = 10
REQUEST_TIMEOUT = 15


class MoMoError(Exception):
    """Any failure talking to MTN.

    A dedicated type lets callers distinguish an upstream failure from a bug
    in our own code, instead of catching bare Exception.
    """


def _require_config() -> None:
    missing = [
        name
        for name in (
            "MOMO_CONSUMER_KEY",
            "MOMO_CONSUMER_SECRET",
            "MOMO_SUBSCRIPTION_KEY",
        )
        if not getattr(settings, name, "")
    ]
    if missing:
        raise MoMoError(f"MoMo is not configured: missing {', '.join(missing)}")


def _get_access_token() -> str:
    _require_config()

    credentials = base64.b64encode(
        f"{settings.MOMO_CONSUMER_KEY}:{settings.MOMO_CONSUMER_SECRET}".encode()
    ).decode()

    try:
        resp = requests.post(
            f"{settings.MOMO_BASE_URL}/v1/oauth/access_token",
            params={"grant_type": "client_credentials"},
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type":  "application/x-www-form-urlencoded",
            },
            timeout=TOKEN_TIMEOUT,
        )
        resp.raise_for_status()
        token = resp.json().get("access_token")
    except requests.RequestException as exc:
        # Never log the response body here: it carries the bearer token.
        logger.warning("MoMo token request failed: %s", exc)
        raise MoMoError("Could not authenticate with MTN MoMo.") from exc
    except ValueError as exc:
        raise MoMoError("MTN MoMo returned a malformed token response.") from exc

    if not token:
        raise MoMoError("MTN MoMo returned no access token.")
    return token


def _to_msisdn(phone: str) -> str:
    """Normalise to 233XXXXXXXXX (no + prefix)."""
    phone = str(phone or "").strip().replace(" ", "")
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("0"):
        phone = "233" + phone[1:]
    return phone


def _auth_headers(token: str, correlator: str) -> dict:
    return {
        "Authorization":             f"Bearer {token}",
        "Content-Type":              "application/json",
        "transactionId":             correlator,
        "Ocp-Apim-Subscription-Key": settings.MOMO_SUBSCRIPTION_KEY,
    }


def initiate_momo_payment(payment) -> dict:
    """POST /v2/payments — sends a USSD push to the payer's handset."""
    token      = _get_access_token()
    correlator = str(payment.reference)

    payload = {
        # format() keeps the pesewas. int(float(amount)) charged GHS 10 for a
        # GHS 10.50 handout.
        "amount":             format(payment.amount, "f"),
        "currency":           settings.MOMO_CURRENCY,
        "customerInfo":       {"customerMsisdn": _to_msisdn(payment.momo_number)},
        "serviceCode":        "MP",
        "paymentMethod":      "MoMo",
        "paymentDescription": f"Payment for {payment.handout.title}",
        "correlatorId":       correlator,
        "callbackUrl":        settings.MOMO_CALLBACK_URL,
    }

    try:
        resp = requests.post(
            f"{settings.MOMO_BASE_URL}/v2/payments",
            json=payload,
            headers=_auth_headers(token, correlator),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.warning("MoMo initiate failed for %s: %s", correlator, exc)
        raise MoMoError("Could not reach MTN MoMo.") from exc

    if resp.status_code not in (200, 201, 202):
        logger.warning(
            "MoMo initiate rejected %s with HTTP %s", correlator, resp.status_code
        )
        raise MoMoError("MTN MoMo rejected the payment request.")

    return {"reference": correlator, "status": "pending"}


def verify_payment(reference: str) -> dict:
    """GET /v2/payments/{correlatorId} → PENDING | SUCCESSFUL | FAILED | CANCELLED"""
    token = _get_access_token()

    try:
        resp = requests.get(
            f"{settings.MOMO_BASE_URL}/v2/payments/{reference}",
            # The subscription key was missing here, so verification 401'd even
            # when initiation had worked.
            headers=_auth_headers(token, str(reference)),
            timeout=TOKEN_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.warning("MoMo verify failed for %s: %s", reference, exc)
        raise MoMoError("Could not verify the payment with MTN MoMo.") from exc
    except ValueError as exc:
        raise MoMoError("MTN MoMo returned a malformed verification response.") from exc
