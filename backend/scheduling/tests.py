from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase

from branches.models import Branch, Subject, SubjectStatus
from students_and_groups.models import Group, Student, StudentStatus
from users.models import User

from . import services
from .models import Attendance, Lesson, LessonStatus, LessonTemplate


class SchedulingTestCase(TestCase):
    def setUp(self):
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
            phone="+1000000001",
            password="x",
            first_name="T",
            last_name="One",
            role="TEACHER",
        )
        self.other_teacher = User.objects.create_user(
            phone="+1000000002",
            password="x",
            first_name="T",
            last_name="Two",
            role="TEACHER",
        )
        self.student = Student.objects.create(
            first_name="S",
            last_name="A",
            branch=self.branch,
            status=StudentStatus.ACTIVE,
        )
        self.group = Group.objects.create(
            name="G1",
            branch=self.branch,
        )
        self.group.students.add(self.student)


class CheckConflictsTests(SchedulingTestCase):
    def test_teacher_overlap_is_conflict(self):
        Lesson.objects.create(
            name="L1",
            date=date(2026, 6, 1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
        )
        ids = services.check_conflicts(
            teacher_id=self.teacher.pk,
            student_ids=[999],
            date=date(2026, 6, 1),
            start_time=time(10, 30),
            end_time=time(11, 30),
            exclude_lesson_id=None,
        )
        self.assertEqual(len(ids), 1)

    def test_adjacent_slots_not_conflict(self):
        Lesson.objects.create(
            name="L1",
            date=date(2026, 6, 2),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
        )
        ids = services.check_conflicts(
            teacher_id=self.teacher.pk,
            student_ids=[self.student.pk],
            date=date(2026, 6, 2),
            start_time=time(11, 0),
            end_time=time(12, 0),
            exclude_lesson_id=None,
        )
        self.assertEqual(ids, [])

    def test_cancelled_ignored(self):
        Lesson.objects.create(
            name="L1",
            date=date(2026, 6, 3),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=LessonStatus.CANCELLED,
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
        )
        ids = services.check_conflicts(
            teacher_id=self.teacher.pk,
            student_ids=[self.student.pk],
            date=date(2026, 6, 3),
            start_time=time(10, 30),
            end_time=time(11, 30),
            exclude_lesson_id=None,
        )
        self.assertEqual(ids, [])

    def test_exclude_lesson_id(self):
        a = Lesson.objects.create(
            name="L1",
            date=date(2026, 6, 4),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
        )
        ids = services.check_conflicts(
            teacher_id=self.teacher.pk,
            student_ids=[self.student.pk],
            date=date(2026, 6, 4),
            start_time=time(10, 0),
            end_time=time(11, 0),
            exclude_lesson_id=a.pk,
        )
        self.assertEqual(ids, [])


class LessonModelTests(SchedulingTestCase):
    def test_xor_both_student_and_group(self):
        lesson = Lesson(
            name="Bad",
            date=date(2026, 7, 1),
            start_time=time(9, 0),
            end_time=time(10, 0),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
            group=self.group,
        )
        with self.assertRaises(ValidationError):
            lesson.full_clean()

    def test_xor_neither(self):
        lesson = Lesson(
            name="Bad",
            date=date(2026, 7, 1),
            start_time=time(9, 0),
            end_time=time(10, 0),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
        )
        with self.assertRaises(ValidationError):
            lesson.full_clean()

    def test_schedule_conflict_raises(self):
        Lesson.objects.create(
            name="L1",
            date=date(2026, 8, 1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
        )
        lesson = Lesson(
            name="L2",
            date=date(2026, 8, 1),
            start_time=time(10, 30),
            end_time=time(11, 30),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
        )
        with self.assertRaises(services.ScheduleConflict):
            lesson.full_clean()


class LessonTemplateModelTests(SchedulingTestCase):
    def test_template_xor(self):
        t = LessonTemplate(
            name="T",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
            days_of_week=[1],
            start_time=time(10, 0),
            end_time=time(11, 0),
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
            group=self.group,
        )
        with self.assertRaises(ValidationError):
            t.full_clean()


class AttendanceModelTests(SchedulingTestCase):
    def setUp(self):
        super().setUp()
        self.lesson = Lesson.objects.create(
            name="L",
            date=date(2026, 10, 1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
            student=self.student,
        )

    def test_unique_lesson_student(self):
        Attendance.objects.create(
            lesson=self.lesson,
            student=self.student,
            status="present",
        )
        with self.assertRaises(ValidationError):
            Attendance.objects.create(
                lesson=self.lesson,
                student=self.student,
                status="absent",
            )

    def test_no_attendance_on_cancelled(self):
        self.lesson.status = LessonStatus.CANCELLED
        self.lesson.save(update_fields=["status"])
        att = Attendance(
            lesson=self.lesson,
            student=self.student,
            status="present",
        )
        with self.assertRaises(ValidationError):
            att.full_clean()

    def test_wrong_student_group_lesson(self):
        gl = Lesson.objects.create(
            name="GL",
            date=date(2026, 10, 2),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=LessonStatus.SCHEDULED,
            teacher=self.teacher,
            subject=self.subject,
            group=self.group,
        )
        other = Student.objects.create(
            first_name="O",
            last_name="B",
            branch=self.branch,
        )
        att = Attendance(lesson=gl, student=other, status="present")
        with self.assertRaises(ValidationError):
            att.full_clean()
