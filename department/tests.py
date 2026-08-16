from django.urls import reverse

from Handout.testing import ApiTestCase

from .models import Department


class DepartmentListTests(ApiTestCase):
    def setUp(self):
        self.active = Department.objects.create(
            name="Computer Science", department_type="hnd", is_active=True
        )
        Department.objects.create(
            name="Retired", department_type="btech", is_active=False
        )

    def test_is_readable_without_authentication(self):
        # The signup form needs this before the user has an account.
        response = self.client.get(reverse("department-list"))
        self.assertEqual(response.status_code, 200)

    def test_lists_only_active_departments(self):
        response = self.client.get(reverse("department-list"))
        self.assertEqual([d["id"] for d in response.data], [self.active.id])

    def test_is_read_only(self):
        response = self.client.post(
            reverse("department-list"), {"name": "New", "department_type": "hnd"}
        )
        self.assertEqual(response.status_code, 405)
