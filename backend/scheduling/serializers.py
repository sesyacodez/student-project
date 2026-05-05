from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from branches.models import Subject, SubjectStatus
from branches.serializers import BranchSummarySerializer, SubjectSerializer
from students_and_groups.models import Group, Student
from students_and_groups.serializers import StudentSummarySerializer
from users.models import User

from . import services
from .models import Attendance, Lesson, LessonStatus, LessonTemplate


class TeacherSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "phone", "first_name", "last_name", "role")


class GroupSummarySerializer(serializers.ModelSerializer):
    branch = BranchSummarySerializer(read_only=True)

    class Meta:
        model = Group
        fields = ("id", "name", "branch", "status")


def _resolve_lesson_participant(instance, attrs):
    student = attrs.get("student")
    if student is None and instance is not None:
        student = instance.student
    group = attrs.get("group")
    if group is None and instance is not None:
        group = instance.group
    return student, group


def _validate_lesson_participant_xor(student, group):
    has_s = student is not None
    has_g = group is not None
    if has_s == has_g:
        raise ValidationError(
            "Specify exactly one of student_id or group_id for the lesson."
        )


def _validate_subject_and_branch(subject, student, group):
    if subject.status != SubjectStatus.ACTIVE:
        raise ValidationError(
            {"subject_id": "Subject is archived and cannot be used for new lessons."}
        )
    branch_id = subject.branch_id
    if student is not None and student.branch_id != branch_id:
        raise ValidationError(
            {"student_id": "Student must belong to the same branch as the subject."}
        )
    if group is not None and group.branch_id != branch_id:
        raise ValidationError(
            {"group_id": "Group must belong to the same branch as the subject."}
        )


class LessonReadSerializer(serializers.ModelSerializer):
    teacher = TeacherSummarySerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    student = StudentSummarySerializer(read_only=True, allow_null=True)
    group = GroupSummarySerializer(read_only=True, allow_null=True)
    lesson_template_id = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Lesson
        fields = (
            "id",
            "name",
            "date",
            "start_time",
            "end_time",
            "status",
            "teacher",
            "subject",
            "student",
            "group",
            "lesson_template_id",
        )


class LessonWriteSerializer(serializers.ModelSerializer):
    teacher_id = serializers.PrimaryKeyRelatedField(
        source="teacher",
        queryset=User.objects.all(),
        write_only=True,
    )
    subject_id = serializers.PrimaryKeyRelatedField(
        source="subject",
        queryset=Subject.objects.select_related("branch").all(),
        write_only=True,
    )
    student_id = serializers.PrimaryKeyRelatedField(
        source="student",
        queryset=Student.objects.select_related("branch").all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    group_id = serializers.PrimaryKeyRelatedField(
        source="group",
        queryset=Group.objects.select_related("branch").all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = Lesson
        fields = (
            "teacher_id",
            "subject_id",
            "student_id",
            "group_id",
            "date",
            "start_time",
            "end_time",
        )

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        student, group = _resolve_lesson_participant(instance, attrs)
        _validate_lesson_participant_xor(student, group)

        subject = attrs.get("subject")
        if subject is None and instance is not None:
            subject = instance.subject
        if subject is None:
            raise ValidationError({"subject_id": "Subject is required."})

        _validate_subject_and_branch(subject, student, group)

        teacher = attrs.get("teacher")
        if teacher is None and instance is not None:
            teacher = instance.teacher
        date = attrs.get("date")
        if date is None and instance is not None:
            date = instance.date
        start_time = attrs.get("start_time")
        if start_time is None and instance is not None:
            start_time = instance.start_time
        end_time = attrs.get("end_time")
        if end_time is None and instance is not None:
            end_time = instance.end_time

        if not all([teacher, date, start_time, end_time]):
            return attrs

        student_ids = services.participant_student_ids(
            student_id=getattr(student, "pk", None),
            group=group,
        )
        conflict_ids = services.check_conflicts(
            teacher_id=teacher.pk,
            student_ids=student_ids,
            date=date,
            start_time=start_time,
            end_time=end_time,
            exclude_lesson_id=getattr(instance, "pk", None),
        )
        if conflict_ids:
            raise services.ScheduleConflict(
                teacher_id=teacher.pk,
                conflict_lesson_ids=conflict_ids,
                message="This time slot overlaps another lesson for the teacher or a student.",
            )
        return attrs

    def create(self, validated_data):
        subject = validated_data["subject"]
        date = validated_data["date"]
        name = f"{subject.name} {date}"
        return Lesson.objects.create(
            name=name,
            status=LessonStatus.SCHEDULED,
            **validated_data,
        )

    def update(self, instance, validated_data):
        subject = validated_data.get("subject", instance.subject)
        date = validated_data.get("date", instance.date)
        validated_data["name"] = f"{subject.name} {date}"
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ConflictCheckSerializer(LessonWriteSerializer):
    """Same fields as lesson create; returns conflict ids instead of raising 409."""

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        student, group = _resolve_lesson_participant(instance, attrs)
        _validate_lesson_participant_xor(student, group)

        subject = attrs.get("subject")
        if subject is None and instance is not None:
            subject = instance.subject
        if subject is None:
            raise ValidationError({"subject_id": "Subject is required."})

        _validate_subject_and_branch(subject, student, group)

        teacher = attrs.get("teacher")
        if teacher is None and instance is not None:
            teacher = instance.teacher
        date = attrs.get("date")
        if date is None and instance is not None:
            date = instance.date
        start_time = attrs.get("start_time")
        if start_time is None and instance is not None:
            start_time = instance.start_time
        end_time = attrs.get("end_time")
        if end_time is None and instance is not None:
            end_time = instance.end_time

        if not all([teacher, date, start_time, end_time]):
            attrs["conflict_lesson_ids"] = []
            return attrs

        student_ids = services.participant_student_ids(
            student_id=getattr(student, "pk", None),
            group=group,
        )
        conflict_ids = services.check_conflicts(
            teacher_id=teacher.pk,
            student_ids=student_ids,
            date=date,
            start_time=start_time,
            end_time=end_time,
            exclude_lesson_id=getattr(instance, "pk", None),
        )
        attrs["conflict_lesson_ids"] = conflict_ids
        return attrs


class LessonTemplateReadSerializer(serializers.ModelSerializer):
    teacher = TeacherSummarySerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    student = StudentSummarySerializer(read_only=True, allow_null=True)
    group = GroupSummarySerializer(read_only=True, allow_null=True)

    class Meta:
        model = LessonTemplate
        fields = (
            "id",
            "name",
            "start_date",
            "end_date",
            "days_of_week",
            "start_time",
            "end_time",
            "is_active",
            "teacher",
            "subject",
            "student",
            "group",
        )


class LessonTemplateWriteSerializer(serializers.ModelSerializer):
    teacher_id = serializers.PrimaryKeyRelatedField(
        source="teacher",
        queryset=User.objects.all(),
        write_only=True,
    )
    subject_id = serializers.PrimaryKeyRelatedField(
        source="subject",
        queryset=Subject.objects.select_related("branch").all(),
        write_only=True,
    )
    student_id = serializers.PrimaryKeyRelatedField(
        source="student",
        queryset=Student.objects.select_related("branch").all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    group_id = serializers.PrimaryKeyRelatedField(
        source="group",
        queryset=Group.objects.select_related("branch").all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = LessonTemplate
        fields = (
            "teacher_id",
            "subject_id",
            "student_id",
            "group_id",
            "days_of_week",
            "start_time",
            "end_time",
            "start_date",
            "end_date",
            "is_active",
        )

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        student = attrs.get("student")
        if student is None and instance is not None:
            student = instance.student
        group = attrs.get("group")
        if group is None and instance is not None:
            group = instance.group
        _validate_lesson_participant_xor(student, group)

        subject = attrs.get("subject")
        if subject is None and instance is not None:
            subject = instance.subject
        if subject is None:
            raise ValidationError({"subject_id": "Subject is required."})

        _validate_subject_and_branch(subject, student, group)
        return attrs

    def create(self, validated_data):
        subject = validated_data["subject"]
        name = f"{subject.name} recurring"
        return LessonTemplate.objects.create(name=name, **validated_data)

    def update(self, instance, validated_data):
        subject = validated_data.get("subject", instance.subject)
        validated_data.setdefault("name", f"{subject.name} recurring")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class AttendanceReadSerializer(serializers.ModelSerializer):
    student = StudentSummarySerializer(read_only=True)

    class Meta:
        model = Attendance
        fields = ("id", "student", "status", "note")


class AttendancePatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ("status", "note")

    def validate_status(self, value):
        normalized = str(value).strip().lower()
        if normalized not in ("present", "absent"):
            raise ValidationError("Status must be present or absent.")
        return normalized


class AttendanceRecordSerializer(serializers.Serializer):
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.select_related("branch").all(),
        source="student",
    )
    status = serializers.CharField()
    note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_status(self, value):
        normalized = str(value).strip().lower()
        if normalized not in ("present", "absent"):
            raise ValidationError("Status must be present or absent.")
        return normalized


class AttendanceBatchSerializer(serializers.Serializer):
    records = AttendanceRecordSerializer(many=True)

    def validate_records(self, records):
        if not records:
            raise ValidationError("Provide at least one attendance record.")
        return records

    def save(self):
        lesson = self.context["lesson"]
        if lesson.status == LessonStatus.CANCELLED:
            raise ValidationError(
                "Cannot mark attendance for a cancelled lesson."
            )

        for item in self.validated_data["records"]:
            student = item["student"]
            if lesson.student_id:
                if student.pk != lesson.student_id:
                    raise ValidationError(
                        {
                            "records": (
                                f"Student {student.pk} is not in this lesson."
                            )
                        }
                    )
            elif lesson.group_id:
                if not lesson.group.students.filter(pk=student.pk).exists():
                    raise ValidationError(
                        {
                            "records": (
                                f"Student {student.pk} is not in this lesson."
                            )
                        }
                    )

            Attendance.objects.update_or_create(
                lesson=lesson,
                student=student,
                defaults={
                    "status": item["status"],
                    "note": item.get("note") or "",
                },
            )

        return Attendance.objects.filter(lesson=lesson).select_related(
            "student__branch"
        )


class BranchStatsSerializer(serializers.Serializer):
    active_students_count = serializers.IntegerField()
    lessons_completed_count = serializers.IntegerField()
    lessons_cancelled_count = serializers.IntegerField()
    attendance_percent = serializers.FloatField()
