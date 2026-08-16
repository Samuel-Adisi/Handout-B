from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone

from accounts.models import User
from courses.models import Course
from department.models import Department
from handouts.models import Handout
from Handout.testing import ApiTestCase
from payments.models import Payment

from .models import Notification
from .tasks import send_receipt


class ReceiptTests(ApiTestCase):
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
        course = Course.objects.create(rep=self.rep, name="Algorithms", code="CS101")
        self.handout = Handout.objects.create(
            course=course, title="Week 1", price=Decimal("10.50"),
            stock=1, department=self.department,
        )

    def make_payment(self, status="successful", confirmed=True):
        return Payment.objects.create(
            student=self.student,
            handout=self.handout,
            amount=self.handout.price,
            momo_number="0241111111",
            status=status,
            confirmed_at=timezone.now() if confirmed else None,
        )

    def test_notifies_the_student_and_the_rep(self):
        payment = self.make_payment()

        with patch("notifications.utils.send_sms", return_value=True) as send:
            send_receipt(str(payment.id))

        self.assertEqual(send.call_count, 2)
        self.assertEqual(Notification.objects.filter(sent=True).count(), 2)
        self.assertEqual(
            set(Notification.objects.values_list("recipient_id", flat=True)),
            {self.student.id, self.rep.id},
        )

    def test_records_a_failed_delivery_as_unsent(self):
        payment = self.make_payment()

        with patch("notifications.utils.send_sms", return_value=False):
            send_receipt(str(payment.id))

        self.assertEqual(Notification.objects.filter(sent=False).count(), 2)
        self.assertFalse(Notification.objects.exclude(sent_at=None).exists())

    def test_skips_payments_that_are_not_confirmed(self):
        payment = self.make_payment(status="pending", confirmed=False)

        with patch("notifications.utils.send_sms") as send:
            send_receipt(str(payment.id))

        send.assert_not_called()
        self.assertEqual(Notification.objects.count(), 0)

    def test_tolerates_a_missing_confirmed_at(self):
        payment = self.make_payment(confirmed=False)

        with patch("notifications.utils.send_sms", return_value=True):
            send_receipt(str(payment.id))

        self.assertEqual(Notification.objects.count(), 2)

    def test_unknown_payment_is_handled(self):
        self.assertEqual(
            send_receipt("00000000-0000-0000-0000-000000000000"), "Payment not found"
        )
