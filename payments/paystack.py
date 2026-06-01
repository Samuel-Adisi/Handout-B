import requests
from django.conf import settings

PAYSTACK_BASE_URL = "https://api.paystack.co"

def get_momo_network(phone):
    phone = phone.strip().replace(" ", "")
    if phone.startswith("+233"):
        phone = "0" + phone[4:]
    elif phone.startswith("233"):
        phone = "0" + phone[3:]

    prefix = phone[:3]
    mtn        = ["054", "055", "059", "024", "025", "053", "026"]
    vodafone   = ["050", "020"]
    airteltigo = ["027", "057", "056"]

    if prefix in mtn:
        return "mtn"
    elif prefix in vodafone:
        return "vod"
    elif prefix in airteltigo:
        return "tgo"
    else:
        return "mtn"



def initiate_momo_payment(payment):
    network = get_momo_network(payment.momo_number)
    url     = f"{PAYSTACK_BASE_URL}/charge"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "email":        payment.student.email,
        "amount":       int(float(payment.amount) * 100),  # Paystack uses pesewas
        "currency":     "GHS",
        "mobile_money": {
            "phone":    payment.momo_number,
            "provider": network,
        },
        "reference":    payment.reference,
    }
    response = requests.post(url, json=payload, headers=headers)
    print("PAYSTACK STATUS:", response.status_code)
    print("PAYSTACK RESPONSE:", response.json())
    response.raise_for_status()
    return response.json()


def verify_payment(reference):
    """Verify a payment by reference after webhook or polling."""
    url     = f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()