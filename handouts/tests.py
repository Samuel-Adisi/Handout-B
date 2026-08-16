from decimal import Decimal

from django.urls import reverse

from accounts.models import User
from courses.models import Course
from department.models import Department
from Handout.testing import ApiTestCase

from .models import Handout


class HandoutTestData(ApiTestCase):
    def setUp(self):
        self.cs = Department.objects.create(
            name="Computer Science", department_type="hnd", is_active=True
        )
        self.eng = Department.objects.create(
            name="Engineering", department_type="btech", is_active=True
        )

        self.rep = self._user("REP-1", "rep", self.cs, "0201111111")
        self.other_rep = self._user("REP-2", "rep", self.cs, "0202222222")
        self.student = self._user("STU-1", "student", self.cs, "0241111111")
        self.eng_student = self._user("STU-2", "student", self.eng, "0242222222")

        self.course = Course.objects.create(rep=self.rep, name="Algorithms", code="CS101")
        self.other_course = Course.objects.create(
            rep=self.other_rep, name="Networks", code="CS201"
        )

        self.handout = Handout.objects.create(
            course=self.course, title="Week 1", price=Decimal("10.00"),
            stock=5, department=self.cs,
        )

    def _user(self, student_id, role, department, phone):
        return User.objects.create_user(
            student_id=student_id, password="pw", name=student_id,
            phone=phone, role=role, department=department,
        )

    def detail_url(self, handout=None):
        return reverse("handout-detail", args=[(handout or self.handout).id])


class HandoutOwnershipTests(HandoutTestData):
    def test_a_rep_cannot_edit_another_reps_handout(self):
        self.client.force_authenticate(self.other_rep)
        response = self.client.patch(self.detail_url(), {"price": "0.01"})
        self.assertEqual(response.status_code, 404)
        self.handout.refresh_from_db()
        self.assertEqual(self.handout.price, Decimal("10.00"))

    def test_a_rep_cannot_delete_another_reps_handout(self):
        self.client.force_authenticate(self.other_rep)
        response = self.client.delete(self.detail_url())
        self.assertIn(response.status_code, (403, 404))
        self.assertTrue(Handout.objects.filter(pk=self.handout.pk).exists())

    def test_the_owning_rep_can_edit_their_handout(self):
        self.client.force_authenticate(self.rep)
        response = self.client.patch(self.detail_url(), {"price": "12.00"})
        self.assertEqual(response.status_code, 200)
        self.handout.refresh_from_db()
        self.assertEqual(self.handout.price, Decimal("12.00"))

    def test_a_rep_cannot_attach_a_handout_to_a_course_they_do_not_own(self):
        self.client.force_authenticate(self.rep)
        response = self.client.post(
            reverse("handout-list"),
            {
                "title": "Sneaky",
                "price": "5.00",
                "stock": 1,
                "course_id": self.other_course.id,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_students_cannot_create_handouts(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            reverse("handout-list"),
            {"title": "Free", "price": "1.00", "stock": 1, "course_id": self.course.id},
        )
        self.assertEqual(response.status_code, 403)


class HandoutScopeTests(HandoutTestData):
    def test_students_see_only_their_own_department(self):
        self.client.force_authenticate(self.eng_student)
        response = self.client.get(reverse("handout-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

        self.client.force_authenticate(self.student)
        response = self.client.get(reverse("handout-list"))
        self.assertEqual(response.data["count"], 1)

    def test_a_student_cannot_read_another_departments_handout_by_id(self):
        self.client.force_authenticate(self.eng_student)
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, 404)

    def test_a_student_without_a_department_sees_nothing(self):
        self.student.department = None
        self.student.save(update_fields=["department"])

        self.client.force_authenticate(self.student)
        response = self.client.get(reverse("handout-list"))
        self.assertEqual(response.data["count"], 0)

    def test_listing_requires_authentication(self):
        self.assertEqual(self.client.get(reverse("handout-list")).status_code, 401)


class HandoutModelTests(HandoutTestData):
    def test_has_stock_tolerates_a_null_stock(self):
        self.handout.stock = None
        self.assertFalse(self.handout.has_stock())

    def test_department_defaults_to_the_reps_department(self):
        handout = Handout.objects.create(
            course=self.course, title="Week 2", price=Decimal("8.00"), stock=2
        )
        self.assertEqual(handout.department, self.cs)
