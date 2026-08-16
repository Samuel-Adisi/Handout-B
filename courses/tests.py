from django.urls import reverse

from accounts.models import User
from department.models import Department
from Handout.testing import ApiTestCase

from .models import Course


class CourseTestData(ApiTestCase):
    def setUp(self):
        self.cs = Department.objects.create(
            name="Computer Science", department_type="hnd", is_active=True
        )
        self.rep = self._user("REP-1", "rep", "0201111111")
        self.other_rep = self._user("REP-2", "rep", "0202222222")
        self.student = self._user("STU-1", "student", "0241111111")
        self.admin = self._user("ADM-1", "admin", "0209999999")

        self.course = Course.objects.create(rep=self.rep, name="Algorithms", code="CS101")

    def _user(self, student_id, role, phone):
        return User.objects.create_user(
            student_id=student_id, password="pw", name=student_id,
            phone=phone, role=role, department=self.cs,
        )


class CourseOwnershipTests(CourseTestData):
    def test_a_rep_cannot_edit_another_reps_course(self):
        self.client.force_authenticate(self.other_rep)
        response = self.client.patch(
            reverse("course-detail", args=[self.course.id]), {"name": "Hijacked"}
        )
        self.assertEqual(response.status_code, 404)
        self.course.refresh_from_db()
        self.assertEqual(self.course.name, "Algorithms")

    def test_students_cannot_create_a_course(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(reverse("course-list"), {"name": "Fake", "code": "X1"})
        self.assertEqual(response.status_code, 403)

    def test_a_rep_owns_the_course_they_create(self):
        self.client.force_authenticate(self.rep)
        response = self.client.post(
            reverse("course-list"),
            {"name": "Compilers", "code": "CS301", "rep_id": self.other_rep.id},
        )
        self.assertEqual(response.status_code, 201)
        # rep_id from the body is ignored for reps.
        self.assertEqual(Course.objects.get(code="CS301").rep, self.rep)

    def test_an_admin_must_nominate_a_rep(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(reverse("course-list"), {"name": "Compilers", "code": "CS301"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("rep_id", response.data)

    def test_a_rep_cannot_reassign_their_course_to_someone_else(self):
        self.client.force_authenticate(self.rep)
        response = self.client.patch(
            reverse("course-detail", args=[self.course.id]),
            {"rep_id": self.other_rep.id},
        )
        self.assertEqual(response.status_code, 200)
        self.course.refresh_from_db()
        self.assertEqual(self.course.rep, self.rep)


class CourseScopeTests(CourseTestData):
    def test_a_rep_sees_only_their_own_courses(self):
        Course.objects.create(rep=self.other_rep, name="Networks", code="CS201")

        self.client.force_authenticate(self.rep)
        response = self.client.get(reverse("course-list"))
        self.assertEqual(response.data["count"], 1)

    def test_students_see_their_departments_courses(self):
        self.client.force_authenticate(self.student)
        response = self.client.get(reverse("course-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
