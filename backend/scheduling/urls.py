from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import (
    AttendanceViewSet,
    LessonTemplateViewSet,
    LessonViewSet,
    branch_stats_report,
    student_attendance_report,
    teacher_schedule_report,
)

router = DefaultRouter()
router.register("lessons", LessonViewSet, basename="lesson")
router.register("lesson-templates", LessonTemplateViewSet, basename="lesson-template")
router.register("attendance", AttendanceViewSet, basename="attendance")

urlpatterns = router.urls + [
    path("reports/teacher-schedule/", teacher_schedule_report),
    path("reports/student-attendance/", student_attendance_report),
    path("reports/branch-stats/", branch_stats_report),
]
