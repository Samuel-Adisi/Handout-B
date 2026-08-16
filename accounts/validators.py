import re

from rest_framework import serializers

# 0XXXXXXXXX, 233XXXXXXXXX or +233XXXXXXXXX
_LOCAL = re.compile(r"^0\d{9}$")
_INTL = re.compile(r"^(?:\+?233)\d{9}$")


def normalise_gh_phone(value: str) -> str:
    """Validate a Ghanaian mobile number and return it as 0XXXXXXXXX.

    Accepting the international forms as well means a user who types +233...
    is not rejected for a formatting choice.
    """
    phone = re.sub(r"[\s\-()]", "", str(value or ""))

    if _LOCAL.fullmatch(phone):
        return phone
    if _INTL.fullmatch(phone):
        return "0" + phone[-9:]

    raise serializers.ValidationError(
        "Enter a valid Ghana phone number e.g. 0241234567"
    )
