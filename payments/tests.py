from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from accounts.models import User
from courses.models import Course
from department.models import Department
from handouts.models import Handout
from Handout.testing import ApiTestCase

from .models import Payment
from .momo import MoMoError, _to_msisdn
from .services import available_stock, confirm_payment


class PaymentTestData(ApiTestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="Computer Science", department_type="hnd", is_active=True
        )
        self.rep = User.objects.create_user(
            student_id="REP-1", password="pw", name="Rep", phone="0201111111",
            role="rep", department=self.department,
        )
        self.student = User.objects.create_user(
            student_id="STU-1", password="pw", name="Student", phone="0241111111",
            department=self.department,
        )
        self.course = Course.objects.create(rep=self.rep, name="Algorithms", code="CS101")
        self.handout = Handout.objects.create(
            course=self.course, title="Week 1", price=Decimal("10.50"),
            stock=1, department=self.department,
        )

    def make_payment(self, student=None, status="pending"):
        return Payment.objects.create(
            student=student or self.student,
            handout=self.handout,
            amount=self.handout.price,
            momo_number="0241111111",
            status=status,
        )


class CallbackSecurityTests(PaymentTestData):
    """The callback is public; it must never take the caller's word for it."""

    def test_forged_success_callback_does_not_confirm_a_payment(self):
        payment = self.make_payment()

        # MTN is the authority and still says PENDING, whatever the body claims.
        with patch("payments.views.verify_payment", return_value={"status": "PENDING"}):
            response = self.client.post(
                reverse("momo-callback"),
                {"correlatorId": str(payment.reference), "status": "SUCCESSFUL"},
            )

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.handout.refresh_from_db()
        self.assertEqual(payment.status, "pending")
        self.assertEqual(self.handout.stock, 1)

    def test_callback_confirms_only_what_mtn_confirms(self):
        payment = self.make_payment()

        with patch("payments.views.verify_payment", return_value={"status": "SUCCESSFUL"}):
            response = self.client.post(
                reverse("momo-callback"), {"correlatorId": str(payment.reference)}
            )

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.handout.refresh_from_db()
        self.assertEqual(payment.status, "successful")
        self.assertEqual(self.handout.stock, 0)

    def test_callback_rejects_a_bad_shared_secret(self):
        payment = self.make_payment()

        with self.settings(MOMO_CALLBACK_TOKEN="s3cret"):
            response = self.client.post(
                reverse("momo-callback"),
                {"correlatorId": str(payment.reference), "status": "SUCCESSFUL"},
                headers={"X-Callback-Token": "wrong"},
            )

        self.assertEqual(response.status_code, 403)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending")

    def test_unknown_reference_is_acknowledged_without_disclosure(self):
        response = self.client.post(
            reverse("momo-callback"),
            {"correlatorId": "does-not-exist", "status": "SUCCESSFUL"},
        )
        self.assertEqual(response.status_code, 200)

    def test_unverifiable_callback_asks_mtn_to_retry(self):
        payment = self.make_payment()

        with patch("payments.views.verify_payment", side_effect=MoMoError("down")):
            response = self.client.post(
                reverse("momo-callback"), {"correlatorId": str(payment.reference)}
            )

        self.assertEqual(response.status_code, 503)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending")


class ConfirmationTests(PaymentTestData):
    def test_confirming_twice_decrements_stock_once(self):
        payment = self.make_payment()

        confirm_payment(payment.pk)
        confirm_payment(payment.pk)

        self.handout.refresh_from_db()
        self.assertEqual(self.handout.stock, 0)

    def test_stock_never_goes_negative(self):
        self.handout.stock = 0
        self.handout.save(update_fields=["stock"])
        payment = self.make_payment()

        confirm_payment(payment.pk)

        self.handout.refresh_from_db()
        self.assertEqual(self.handout.stock, 0)

    def test_pending_payments_count_against_available_stock(self):
        self.assertEqual(available_stock(self.handout), 1)
        self.make_payment()
        self.assertEqual(available_stock(self.handout), 0)


class InitiationTests(PaymentTestData):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.student)

    def initiate(self, **overrides):
        payload = {"handout_id": self.handout.id, "momo_number": "0241111111"}
        payload.update(overrides)
        with patch("payments.views.initiate_momo_payment", return_value={}):
            return self.client.post(reverse("payment-initiate"), payload)

    def test_charges_the_handout_price_not_the_submitted_one(self):
        response = self.initiate(amount="0.01")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Payment.objects.get().amount, Decimal("10.50"))

    def test_second_buyer_is_refused_while_one_copy_is_reserved(self):
        self.assertEqual(self.initiate().status_code, 201)

        other = User.objects.create_user(
            student_id="STU-2", password="pw", name="Other", phone="0242222222",
            department=self.department,
        )
        self.client.force_authenticate(other)
        response = self.initiate()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Payment.objects.count(), 1)

    def test_cannot_pay_twice_for_the_same_handout(self):
        self.make_payment(status="successful")
        response = self.initiate()
        self.assertEqual(response.status_code, 400)

    def test_a_failed_attempt_can_be_retried(self):
        self.make_payment(status="failed")
        response = self.initiate()
        self.assertEqual(response.status_code, 201)
        # The earlier attempt is kept rather than deleted.
        self.assertEqual(Payment.objects.filter(student=self.student).count(), 2)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        response = self.client.post(
            reverse("payment-initiate"),
            {"handout_id": self.handout.id, "momo_number": "0241111111"},
        )
        self.assertEqual(response.status_code, 401)


class PaymentVisibilityTests(PaymentTestData):
    def test_students_cannot_read_another_student_payment(self):
        other = User.objects.create_user(
            student_id="STU-3", password="pw", name="Other", phone="0243333333",
            department=self.department,
        )
        payment = self.make_payment(student=other)

        self.client.force_authenticate(self.student)
        response = self.client.get(
            reverse("payment-status", args=[str(payment.reference)])
        )
        self.assertEqual(response.status_code, 404)

    def test_my_payments_lists_only_the_caller(self):
        other = User.objects.create_user(
            student_id="STU-4", password="pw", name="Other", phone="0244444444",
            department=self.department,
        )
        self.make_payment(student=self.student)
        self.make_payment(student=other)

        self.client.force_authenticate(self.student)
        response = self.client.get(reverse("my-payments"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)


class MsisdnTests(ApiTestCase):
    def test_normalises_local_and_international_forms(self):
        self.assertEqual(_to_msisdn("0241234567"), "233241234567")
        self.assertEqual(_to_msisdn("+233241234567"), "233241234567")
        self.assertEqual(_to_msisdn("233241234567"), "233241234567")
