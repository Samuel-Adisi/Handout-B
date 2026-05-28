import requests
from django.conf import settings

PAYSTACK_BASE_URL = "https://api.paystack.co"

def get_momo_provider(phone):
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
        return "atl"
    else:
        return "mtn"

def initiate_momo_payment(payment):
    provider = get_momo_provider(payment.momo_number)
    safe_id  = payment.student.student_id.replace("/", "").replace(" ", "").lower()
    email    = f"{safe_id}@hgmail.com"
    url      = f"{PAYSTACK_BASE_URL}/charge"
    headers  = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "amount":    int(payment.amount * 100),
        "email":     email,
        "currency":  "GHS",
        "reference": payment.reference,
        "mobile_money": {
            "phone":    payment.momo_number,
            "provider": provider,
        },
        "metadata": {
            "handout_id": str(payment.handout.id),
            "student_id": str(payment.student.id),
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    print("PAYSTACK STATUS:", response.status_code)
    print("PAYSTACK RESPONSE:", response.json())
    response.raise_for_status()
    return response.json()
