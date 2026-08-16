from django.urls import reverse

from department.models import Department
from Handout.testing import ApiTestCase

from .models import User


class RegistrationTests(ApiTestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="Computer Science", department_type="hnd", is_active=True
        )

    def payload(self, **overrides):
        data = {
            "name": "Ama Mensah",
            "student_id": "CS-0001",
            "phone": "0241234567",
            "password": "correct-horse-staple-9",
            "department_id": self.department.id,
        }
        data.update(overrides)
        return data

    def test_registers_a_student(self):
        response = self.client.post(reverse("register"), self.payload())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(student_id="CS-0001").role, "student")

    def test_cannot_self_assign_a_privileged_role(self):
        response = self.client.post(reverse("register"), self.payload(role="admin"))
        self.assertEqual(response.status_code, 201)
        # role is read-only, so the request succeeds but the value is ignored.
        self.assertEqual(User.objects.get(student_id="CS-0001").role, "student")

    def test_rejects_duplicate_student_id(self):
        self.client.post(reverse("register"), self.payload())
        response = self.client.post(reverse("register"), self.payload(phone="0201234567"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("student_id", response.data)

    def test_rejects_a_malformed_phone_number(self):
        response = self.client.post(reverse("register"), self.payload(phone="12345"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.data)

    def test_accepts_the_international_phone_format(self):
        response = self.client.post(reverse("register"), self.payload(phone="+233241234567"))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(student_id="CS-0001").phone, "0241234567")

    def test_requires_a_department(self):
        payload = self.payload()
        payload.pop("department_id")
        response = self.client.post(reverse("register"), payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("department_id", response.data)


class RepRegistrationTests(ApiTestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="Engineering", department_type="btech", is_active=True
        )
        self.payload = {
            "name": "Kofi Boateng",
            "student_id": "EN-0002",
            "phone": "0201234567",
            "password": "correct-horse-staple-9",
            "department_id": self.department.id,
            "invite_code": "let-me-in",
        }

    def test_rejects_a_wrong_invite_code(self):
        with self.settings(REP_INVITE_CODE="let-me-in"):
            response = self.client.post(
                reverse("register-rep"), {**self.payload, "invite_code": "guess"}
            )
        self.assertEqual(response.status_code, 400)

    def test_accepts_the_configured_invite_code(self):
        with self.settings(REP_INVITE_CODE="let-me-in"):
            response = self.client.post(reverse("register-rep"), self.payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(student_id="EN-0002").role, "rep")

    def test_fails_closed_when_no_invite_code_is_configured(self):
        with self.settings(REP_INVITE_CODE=""):
            response = self.client.post(
                reverse("register-rep"), {**self.payload, "invite_code": ""}
            )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(student_id="EN-0002").exists())


class ProfileTests(ApiTestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="Computer Science", department_type="hnd", is_active=True
        )
        self.user = User.objects.create_user(
            student_id="CS-0100",
            password="correct-horse-staple-9",
            name="Ama Mensah",
            phone="0241234567",
            department=self.department,
        )
        self.client.force_authenticate(self.user)

    def test_cannot_escalate_role_through_profile_update(self):
        response = self.client.patch(reverse("me"), {"role": "admin"})
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, "student")

    def test_cannot_change_student_id(self):
        self.client.patch(reverse("me"), {"student_id": "CS-9999"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.student_id, "CS-0100")

    def test_can_update_own_name_and_phone(self):
        response = self.client.patch(reverse("me"), {"name": "Ama M.", "phone": "0209999999"})
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Ama M.")
        self.assertEqual(self.user.phone, "0209999999")

    def test_profile_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse("me")).status_code, 401)


class SuperuserTests(ApiTestCase):
    def test_superuser_gets_the_admin_role(self):
        user = User.objects.create_superuser(student_id="ADMIN-1", password="pw", name="Root", phone="0241111111")
        self.assertEqual(user.role, "admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
