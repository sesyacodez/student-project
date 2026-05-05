from datetime import date, time

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from branches.models import Branch, Subject, SubjectStatus
from students_and_groups.models import Group, Student, StudentStatus
from users.models import User

from .models import Lesson, LessonStatus


class LessonAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.branch = Branch.objects.create(
            name="Main",
            address="1 St",
            city="Kyiv",
        )
        self.subject = Subject.objects.create(
            name="Math",
            branch=self.branch,
            status=SubjectStatus.ACTIVE,
        )
        self.teacher = User.objects.create_user(
            phone="+2000000001",
            password="secret",
            first_name="Tea",
            last_name="Cher",
            role="TEACHER",
        )
        self.admin = User.objects.create_user(
            phone="+2000000002",
            password="secret",
            first_name="Ad",
            last_name="Min",
            role="ADMIN",
        )
        self.student = Student.objects.create(
            first_name="Stu",
            last_name="Dent",
            branch=self.branch,
            status=StudentStatus.ACTIVE,
        )

    def test_create_lesson_201(self):
        res = self.client.post(
            "/api/v1/lessons/",
            {
                "teacher_id": self.teacher.pk,
                "subject_id": self.subject.pk,
                "student_id": self.student.pk,
                "group_id": None,
                "date": "2026-11-01",
                "start_time": "09:00:00",
                "end_time": "10:00:00",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["status"], "scheduled")

    def test_create_lesson_409_conflict(self):
        Lesson.objects.create(
            name="Existing",
            date=date(2026, 11, 2),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
        )
        res = self.client.post(
            "/api/v1/lessons/",
            {
                "teacher_id": self.teacher.pk,
                "subject_id": self.subject.pk,
                "student_id": self.student.pk,
                "date": "2026-11-02",
                "start_time": "10:30:00",
                "end_time": "11:30:00",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(res.data["code"], "schedule_conflict")

    def test_conflicts_check_returns_ids_without_create(self):
        ex = Lesson.objects.create(
            name="Existing",
            date=date(2026, 11, 3),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
        )
        before = Lesson.objects.count()
        res = self.client.post(
            "/api/v1/lessons/conflicts/check/",
            {
                "teacher_id": self.teacher.pk,
                "subject_id": self.subject.pk,
                "student_id": self.student.pk,
                "date": "2026-11-03",
                "start_time": "10:15:00",
                "end_time": "11:00:00",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ex.pk, res.data["conflict_lesson_ids"])
        self.assertEqual(Lesson.objects.count(), before)

    def test_attendance_batch_upsert(self):
        lesson = Lesson.objects.create(
            name="L",
            date=date(2026, 11, 4),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
        )
        url = f"/api/v1/lessons/{lesson.pk}/attendance/"
        body = {
            "records": [
                {"student_id": self.student.pk, "status": "present", "note": ""},
            ]
        }
        r1 = self.client.put(url, body, format="json")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r1.data), 1)
        r2 = self.client.put(
            url,
            {
                "records": [
                    {
                        "student_id": self.student.pk,
                        "status": "absent",
                        "note": "late",
                    },
                ]
            },
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.data[0]["status"], "absent")

    def test_teacher_list_only_own_lessons(self):
        other = User.objects.create_user(
            phone="+2000000003",
            password="x",
            first_name="O",
            last_name="T",
            role="TEACHER",
        )
        Lesson.objects.create(
            name="Mine",
            date=date(2026, 11, 5),
            start_time=time(9, 0),
            end_time=time(10, 0),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
        )
        Lesson.objects.create(
            name="Yours",
            date=date(2026, 11, 5),
            start_time=time(11, 0),
            end_time=time(12, 0),
            status=LessonStatus.SCHEDULED,
            teacher=other,
            subject=self.subject,
            student=self.student,
        )
        self.client.force_authenticate(user=self.teacher)
        res = self.client.get("/api/v1/lessons/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        names = {row["name"] for row in res.data["results"]}
        self.assertEqual(names, {"Mine"})

    def test_template_generate_skips_conflicts(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(
            "/api/v1/lesson-templates/",
            {
                "teacher_id": self.teacher.pk,
                "subject_id": self.subject.pk,
                "student_id": self.student.pk,
                "group_id": None,
                "days_of_week": [1],
                "start_time": "10:00:00",
                "end_time": "11:00:00",
                "start_date": "2026-11-09",
                "end_date": "2026-11-09",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        tpl_id = r.data["id"]
        Lesson.objects.create(
            name="Block",
            date=date(2026, 11, 9),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
        )
        gen = self.client.post(
            f"/api/v1/lesson-templates/{tpl_id}/generate/",
            {},
            format="json",
        )
        self.assertEqual(gen.status_code, status.HTTP_200_OK)
        self.assertEqual(gen.data["created"], [])
        self.assertTrue(any(s["reason"] == "conflict" for s in gen.data["skipped"]))

    def test_branch_stats_requires_admin(self):
        res = self.client.get(
            f"/api/v1/reports/branch-stats/?branch_id={self.branch.pk}"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=self.admin)
        res2 = self.client.get(
            f"/api/v1/reports/branch-stats/?branch_id={self.branch.pk}"
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertIn("active_students_count", res2.data)
