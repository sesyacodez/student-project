from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from . import services

# Subject у проєкті живе в апці branches; Student/Group — у students_and_groups.


class LessonStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Present"
    ABSENT = "absent", "Absent"


class LessonTemplate(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    days_of_week = models.JSONField(default=list)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_templates",
    )
    subject = models.ForeignKey(
        "branches.Subject",
        on_delete=models.CASCADE,
        related_name="lesson_templates",
    )
    student = models.ForeignKey(
        "students_and_groups.Student",
        on_delete=models.CASCADE,
        related_name="lesson_templates",
        null=True,
        blank=True,
    )
    group = models.ForeignKey(
        "students_and_groups.Group",
        on_delete=models.CASCADE,
        related_name="lesson_templates",
        null=True,
        blank=True,
    )

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(
                {"end_date": "End date must be on or after start date."}
            )
        if (
            self.start_time
            and self.end_time
            and self.start_time >= self.end_time
        ):
            raise ValidationError(
                {"end_time": "End time must be after start time."}
            )

        has_student = bool(self.student_id)
        has_group = bool(self.group_id)
        if has_student == has_group:
            raise ValidationError(
                "Specify exactly one of student or group for the template."
            )

        days = self.days_of_week or []
        if not isinstance(days, list) or not days:
            raise ValidationError(
                {
                    "days_of_week": (
                        "Provide at least one weekday (1=Monday … 7=Sunday)."
                    )
                }
            )
        seen = set()
        for day in days:
            if not isinstance(day, int) or day < 1 or day > 7:
                raise ValidationError(
                    {
                        "days_of_week": (
                            "Each weekday must be an integer from 1 to 7."
                        )
                    }
                )
            if day in seen:
                raise ValidationError(
                    {"days_of_week": "Weekdays must be unique."}
                )
            seen.add(day)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Lesson(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(
        max_length=9,
        choices=LessonStatus.choices,
        default=LessonStatus.SCHEDULED,
    )
    lesson_template = models.ForeignKey(
        "scheduling.LessonTemplate",
        on_delete=models.SET_NULL,
        related_name="lessons",
        null=True,
        blank=True,
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    subject = models.ForeignKey(
        "branches.Subject",
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    student = models.ForeignKey(
        "students_and_groups.Student",
        on_delete=models.CASCADE,
        related_name="lessons",
        null=True,
        blank=True,
    )
    group = models.ForeignKey(
        "students_and_groups.Group",
        on_delete=models.CASCADE,
        related_name="lessons",
        null=True,
        blank=True,
    )

    def clean(self):
        super().clean()

        if (
            self.start_time
            and self.end_time
            and self.start_time >= self.end_time
        ):
            raise ValidationError(
                {"end_time": "End time must be after start time."}
            )

        has_student = bool(self.student_id)
        has_group = bool(self.group_id)
        if has_student == has_group:
            raise ValidationError(
                "Specify exactly one of student or group for the lesson."
            )

        if not all(
            [self.teacher_id, self.date, self.start_time, self.end_time]
        ):
            return

        group = self.group if self.group_id else None
        student_ids = services.participant_student_ids(
            student_id=self.student_id,
            group=group,
        )
        conflict_ids = services.check_conflicts(
            teacher_id=self.teacher_id,
            student_ids=student_ids,
            date=self.date,
            start_time=self.start_time,
            end_time=self.end_time,
            exclude_lesson_id=self.pk,
        )
        if conflict_ids:
            raise services.ScheduleConflict(
                teacher_id=self.teacher_id,
                conflict_lesson_ids=conflict_ids,
                message="This time slot overlaps another lesson for the teacher or a student.",
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.name} on {self.date} from {self.start_time} to "
            f"{self.end_time} ({self.status})"
        )


class Attendance(models.Model):
    status = models.CharField(
        max_length=10,
        choices=AttendanceStatus.choices,
    )
    note = models.TextField(blank=True, null=True)
    lesson = models.ForeignKey(
        "scheduling.Lesson",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    student = models.ForeignKey(
        "students_and_groups.Student",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "student"],
                name="unique_attendance_lesson_student",
            )
        ]

    def clean(self):
        super().clean()
        if not self.lesson_id:
            return
        if self.lesson.status == LessonStatus.CANCELLED:
            raise ValidationError(
                {"lesson": "Cannot record attendance for a cancelled lesson."}
            )

        lesson = self.lesson
        if lesson.student_id:
            if self.student_id != lesson.student_id:
                raise ValidationError(
                    {
                        "student": (
                            "Student is not a participant of this lesson."
                        )
                    }
                )
        elif lesson.group_id:
            if not lesson.group.students.filter(pk=self.student_id).exists():
                raise ValidationError(
                    {
                        "student": (
                            "Student is not a participant of this lesson."
                        )
                    }
                )
        else:
            raise ValidationError(
                {"lesson": "Lesson has no valid participant."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
