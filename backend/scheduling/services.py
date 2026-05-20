"""Scheduling бізнес логіка"""

from django.db.models import Q
from rest_framework.exceptions import APIException


class ScheduleConflict(APIException):
    status_code = 409
    default_detail = "Lesson conflicts with an existing schedule."
    default_code = "schedule_conflict"

    def __init__(self, *, teacher_id=None, conflict_lesson_ids=None, message=None):
        detail = {
            "code": "schedule_conflict",
            "message": message or str(self.default_detail),
            "details": {
                "teacher_id": teacher_id,
                "conflict_lesson_ids": list(conflict_lesson_ids or []),
            },
        }
        super().__init__(detail=detail)


def participant_student_ids(*, student_id=None, group=None):
    if student_id:
        return [student_id]
    if group is not None:
        return list(group.students.values_list("pk", flat=True))
    return []


def check_conflicts(
    *,
    teacher_id,
    student_ids,
    date,
    start_time,
    end_time,
    exclude_lesson_id=None,
):
    """повертає ID не скасованих уроків які перетинаються з вказаним уроком"""
    from scheduling.models import Lesson

    qs = Lesson.objects.filter(date=date).exclude(status="cancelled")
    if exclude_lesson_id is not None:
        qs = qs.exclude(pk=exclude_lesson_id)

    qs = qs.filter(
        start_time__lt=end_time,
        end_time__gt=start_time,
    )

    overlap = Q(teacher_id=teacher_id)
    if student_ids:
        overlap |= Q(student_id__in=student_ids) | Q(group__students__in=student_ids)

    qs = qs.filter(overlap)
    return list(qs.values_list("id", flat=True).distinct())
