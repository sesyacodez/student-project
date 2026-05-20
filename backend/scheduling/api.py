from datetime import timedelta

from django.db.models import Count, Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from students_and_groups.models import Student, StudentStatus

from . import services
from .models import Attendance, Lesson, LessonStatus, LessonTemplate
from .permissions import (
    IsAdminOrLessonTeacher,
    IsAdminOrTeacherUserRole,
    IsAdminUserRole,
    is_teacher_user,
)
from .serializers import (
    AttendanceBatchSerializer,
    AttendancePatchSerializer,
    AttendanceReadSerializer,
    BranchStatsSerializer,
    ConflictCheckSerializer,
    LessonReadSerializer,
    LessonTemplateReadSerializer,
    LessonTemplateWriteSerializer,
    LessonWriteSerializer,
)


def _normalize_choice(value, allowed_values, field_name):
    if value in (None, ""):
        return None
    normalized = str(value).strip().lower()
    if normalized not in allowed_values:
        raise ValidationError(
            {
                field_name: (
                    f"Expected one of: {', '.join(sorted(allowed_values))}."
                )
            }
        )
    return normalized


def _student_ids_for_teacher(teacher):
    ids = set(
        Lesson.objects.filter(
            teacher=teacher, student_id__isnull=False
        ).values_list("student_id", flat=True)
    )
    ids.update(
        Lesson.objects.filter(
            teacher=teacher, group_id__isnull=False
        ).values_list("group__students__id", flat=True)
    )
    return {pk for pk in ids if pk is not None}


class LessonViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, IsAdminOrTeacherUserRole]

    def get_permissions(self):
        if self.action in (
            "create",
            "update",
            "partial_update",
            "cancel",
            "conflicts_check",
        ):
            return [IsAuthenticated(), IsAdminUserRole()]
        if self.action in ("complete", "attendance_collection"):
            return [IsAuthenticated(), IsAdminOrLessonTeacher()]
        return [permission() for permission in self.permission_classes]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return LessonWriteSerializer
        return LessonReadSerializer

    def get_queryset(self):
        queryset = (
            Lesson.objects.select_related(
                "teacher",
                "subject",
                "subject__branch",
                "student",
                "student__branch",
                "group",
                "group__branch",
            )
            .prefetch_related("group__students")
            .order_by("date", "start_time")
        )
        params = self.request.query_params

        branch_id = params.get("branch_id")
        teacher_id = params.get("teacher_id")
        student_id = params.get("student_id")
        group_id = params.get("group_id")
        subject_id = params.get("subject_id")
        status_value = _normalize_choice(
            params.get("status"),
            LessonStatus.values,
            "status",
        )
        date_from = params.get("date_from")
        date_to = params.get("date_to")

        if branch_id:
            queryset = queryset.filter(subject__branch_id=branch_id)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if student_id:
            queryset = queryset.filter(
                Q(student_id=student_id)
                | Q(group__students__id=student_id)
            )
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        if is_teacher_user(self.request.user):
            queryset = queryset.filter(teacher=self.request.user)

        return queryset.distinct()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson = serializer.save()
        read = LessonReadSerializer(
            lesson, context=self.get_serializer_context()
        )
        return Response(read.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        lesson = serializer.save()
        read = LessonReadSerializer(
            lesson, context=self.get_serializer_context()
        )
        return Response(read.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        lesson = self.get_object()
        lesson.status = LessonStatus.CANCELLED
        lesson.save(update_fields=["status"])
        return Response(
            LessonReadSerializer(
                lesson, context=self.get_serializer_context()
            ).data
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        lesson = self.get_object()
        if lesson.status == LessonStatus.CANCELLED:
            raise ValidationError(
                {"detail": "Cannot complete a cancelled lesson."}
            )
        lesson.status = LessonStatus.COMPLETED
        lesson.save(update_fields=["status"])
        return Response(
            LessonReadSerializer(
                lesson, context=self.get_serializer_context()
            ).data
        )

    @action(detail=False, methods=["post"], url_path="conflicts/check")
    def conflicts_check(self, request):
        serializer = ConflictCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data.get("conflict_lesson_ids", [])
        return Response({"conflict_lesson_ids": ids})

    @action(detail=True, methods=["get", "put"], url_path="attendance")
    def attendance_collection(self, request, pk=None):
        lesson = self.get_object()
        if request.method == "GET":
            records = lesson.attendance_records.select_related(
                "student__branch"
            )
            return Response(
                AttendanceReadSerializer(records, many=True).data
            )
        batch = AttendanceBatchSerializer(
            data=request.data, context={"lesson": lesson}
        )
        batch.is_valid(raise_exception=True)
        batch.save()
        records = lesson.attendance_records.select_related("student__branch")
        return Response(AttendanceReadSerializer(records, many=True).data)


class LessonTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get_queryset(self):
        queryset = (
            LessonTemplate.objects.select_related(
                "teacher",
                "subject",
                "subject__branch",
                "student",
                "student__branch",
                "group",
                "group__branch",
            )
            .order_by("start_date", "name")
        )
        params = self.request.query_params
        branch_id = params.get("branch_id")
        teacher_id = params.get("teacher_id")
        subject_id = params.get("subject_id")
        is_active = params.get("is_active")

        if branch_id:
            queryset = queryset.filter(subject__branch_id=branch_id)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if is_active not in (None, ""):
            v = str(is_active).strip().lower()
            if v in ("true", "1", "yes"):
                queryset = queryset.filter(is_active=True)
            elif v in ("false", "0", "no"):
                queryset = queryset.filter(is_active=False)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return LessonTemplateWriteSerializer
        return LessonTemplateReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = serializer.save()
        read = LessonTemplateReadSerializer(
            template, context=self.get_serializer_context()
        )
        return Response(read.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        template = serializer.save()
        read = LessonTemplateReadSerializer(
            template, context=self.get_serializer_context()
        )
        return Response(read.data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        template = self.get_object()
        template.is_active = False
        template.save(update_fields=["is_active"])
        return Response(
            LessonTemplateReadSerializer(
                template, context=self.get_serializer_context()
            ).data
        )

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        template = self.get_object()
        if not template.is_active:
            raise ValidationError(
                {"detail": "Template is not active; activate it or use another template."}
            )
        subject = template.subject
        created_ids = []
        skipped = []
        weekdays = set(template.days_of_week or [])
        day = template.start_date
        end = template.end_date
        while day <= end:
            if day.isoweekday() in weekdays:
                if Lesson.objects.filter(
                    lesson_template=template, date=day
                ).exists():
                    skipped.append(
                        {
                            "date": day.isoformat(),
                            "reason": "exists",
                            "conflict_lesson_ids": [],
                        }
                    )
                else:
                    student_ids = services.participant_student_ids(
                        student_id=template.student_id,
                        group=template.group if template.group_id else None,
                    )
                    conflict_ids = services.check_conflicts(
                        teacher_id=template.teacher_id,
                        student_ids=student_ids,
                        date=day,
                        start_time=template.start_time,
                        end_time=template.end_time,
                        exclude_lesson_id=None,
                    )
                    if conflict_ids:
                        skipped.append(
                            {
                                "date": day.isoformat(),
                                "reason": "conflict",
                                "conflict_lesson_ids": conflict_ids,
                            }
                        )
                    else:
                        lesson = Lesson(
                            name=f"{subject.name} {day}",
                            date=day,
                            start_time=template.start_time,
                            end_time=template.end_time,
                            status=LessonStatus.SCHEDULED,
                            lesson_template=template,
                            teacher=template.teacher,
                            subject=template.subject,
                            student=template.student,
                            group=template.group,
                        )
                        lesson.save()
                        created_ids.append(lesson.pk)
            day += timedelta(days=1)
        return Response({"created": created_ids, "skipped": skipped})

    @action(detail=False, methods=["post"], url_path="preview-conflicts")
    def preview_conflicts(self, request):
        serializer = LessonTemplateWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        teacher = data["teacher"]
        subject = data["subject"]
        student = data.get("student")
        group = data.get("group")
        start_date = data["start_date"]
        end_date = data["end_date"]
        days = data["days_of_week"] or []
        weekdays = set(days)
        out = []
        day = start_date
        while day <= end_date:
            if day.isoweekday() in weekdays:
                sids = services.participant_student_ids(
                    student_id=getattr(student, "pk", None),
                    group=group,
                )
                cids = services.check_conflicts(
                    teacher_id=teacher.pk,
                    student_ids=sids,
                    date=day,
                    start_time=data["start_time"],
                    end_time=data["end_time"],
                    exclude_lesson_id=None,
                )
                if cids:
                    out.append(
                        {"date": day.isoformat(), "conflict_lesson_ids": cids}
                    )
            day += timedelta(days=1)
        return Response({"dates": out})


class AttendanceViewSet(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = AttendancePatchSerializer
    permission_classes = [IsAuthenticated, IsAdminOrLessonTeacher]
    queryset = Attendance.objects.select_related(
        "lesson", "lesson__teacher", "student"
    )

    def get_queryset(self):
        qs = super().get_queryset()
        if is_teacher_user(self.request.user):
            qs = qs.filter(lesson__teacher=self.request.user)
        return qs


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminOrTeacherUserRole])
def teacher_schedule_report(request):
    teacher_id = request.query_params.get("teacher_id")
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    if is_teacher_user(request.user):
        teacher_id = str(request.user.pk)
    if not teacher_id:
        raise ValidationError(
            {"teacher_id": "Required when not authenticated as a teacher."}
        )

    qs = Lesson.objects.filter(teacher_id=teacher_id).order_by(
        "date", "start_time"
    )
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    qs = qs.select_related(
        "teacher",
        "subject",
        "subject__branch",
        "student",
        "student__branch",
        "group",
        "group__branch",
    )
    return Response(LessonReadSerializer(qs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminOrTeacherUserRole])
def student_attendance_report(request):
    student_id = request.query_params.get("student_id")
    subject_id = request.query_params.get("subject_id")
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    if not student_id:
        raise ValidationError({"student_id": "Required."})

    if request.user.is_authenticated and is_teacher_user(request.user):
        allowed = _student_ids_for_teacher(request.user)
        if int(student_id) not in allowed:
            raise PermissionDenied(
                "You can only view attendance for students in your lessons."
            )

    qs = Attendance.objects.filter(student_id=student_id).select_related(
        "lesson", "lesson__subject"
    )
    if subject_id:
        qs = qs.filter(lesson__subject_id=subject_id)
    if date_from:
        qs = qs.filter(lesson__date__gte=date_from)
    if date_to:
        qs = qs.filter(lesson__date__lte=date_to)

    rows = []
    attended = 0
    missed = 0
    for att in qs.order_by("lesson__date", "lesson__start_time"):
        rows.append(
            {
                "lesson_id": att.lesson_id,
                "date": att.lesson.date,
                "subject_name": att.lesson.subject.name,
                "status": att.status,
                "note": att.note or "",
            }
        )
        if att.status == "present":
            attended += 1
        else:
            missed += 1

    return Response(
        {
            "records": rows,
            "summary": {"attended": attended, "missed": missed},
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUserRole])
def branch_stats_report(request):
    branch_id = request.query_params.get("branch_id")
    if not branch_id:
        raise ValidationError({"branch_id": "Required."})
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    lesson_qs = Lesson.objects.filter(subject__branch_id=branch_id)
    if date_from:
        lesson_qs = lesson_qs.filter(date__gte=date_from)
    if date_to:
        lesson_qs = lesson_qs.filter(date__lte=date_to)

    agg = lesson_qs.aggregate(
        completed=Count("id", filter=Q(status=LessonStatus.COMPLETED)),
        cancelled=Count("id", filter=Q(status=LessonStatus.CANCELLED)),
    )
    active_students = Student.objects.filter(
        branch_id=branch_id, status=StudentStatus.ACTIVE
    ).count()

    attendance_qs = Attendance.objects.filter(
        lesson__subject__branch_id=branch_id
    )
    if date_from:
        attendance_qs = attendance_qs.filter(lesson__date__gte=date_from)
    if date_to:
        attendance_qs = attendance_qs.filter(lesson__date__lte=date_to)
    total = attendance_qs.count()
    present = attendance_qs.filter(status="present").count()
    pct = (present / total * 100.0) if total else 0.0

    payload = {
        "active_students_count": active_students,
        "lessons_completed_count": agg["completed"] or 0,
        "lessons_cancelled_count": agg["cancelled"] or 0,
        "attendance_percent": round(pct, 2),
    }
    serializer = BranchStatsSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.data)
