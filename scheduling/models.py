from django.conf import settings
from django.db import models

# Посилання на Subject, Student та Group з апки branches
# на момент створення цих моделей вони ще не існують
# за потреби доведеться імпортувати їх пізніше або використовувати рядкові посилання (поки що так і є (branches.))


class LessonTemplate(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    days_of_week = models.MultipleChoiceField(
        max_length=20,
        choices=[
            ("mon", "Monday"),
            ("tue", "Tuesday"),
            ("wed", "Wednesday"),
            ("thu", "Thursday"),
            ("fri", "Friday"),
            ("sat", "Saturday"),
            ("sun", "Sunday"),
        ],
    )
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
        "branches.Student",
        on_delete=models.CASCADE,
        related_name="lesson_templates",
        null=True,
        blank=True,
    )
    group = models.ForeignKey(
        "branches.Group",
        on_delete=models.CASCADE,
        related_name="lesson_templates",
        null=True,
        blank=True,
    )


class Lesson(models.Model):
    CANCELLED_STATUS = "cancelled"

    name = models.CharField(max_length=100)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(
        max_length=9,
        choices=[
            ("scheduled", "Scheduled"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
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
        "branches.Student",
        on_delete=models.CASCADE,
        related_name="lessons",
        null=True,
        blank=True,
    )
    group = models.ForeignKey(
        "branches.Group",
        on_delete=models.CASCADE,
        related_name="lessons",
        null=True,
        blank=True,
    )

    # треба ще реалізувати уникнення кофліктів (student-project-spec.md пункт 4.7.3)


    def __str__(self):
        return f"{self.name} on {self.date} from {self.start_time} to {self.end_time} ({self.status})"


class Attendance(models.Model):
    status = models.CharField(
        max_length=10,
        choices=[
            ("present", "Present"),
            ("absent", "Absent"),
        ],
    )
    note = models.TextField(blank=True, null=True)
    lesson = models.ForeignKey(
        "scheduling.Lesson",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    student = models.ForeignKey(
        "branches.Student",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
