from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase


@override_settings(
    # The throttle counters live in the cache and would otherwise leak between
    # tests, so an unrelated test could fail with 429.
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class ApiTestCase(APITestCase):
    """Base case for API tests: isolated throttle state and fast hashing."""

    def _pre_setup(self):
        super()._pre_setup()
        cache.clear()
