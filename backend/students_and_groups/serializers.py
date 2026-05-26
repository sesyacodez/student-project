from django.utils import timezone
from rest_framework import serializers

from branches.models import Branch
from branches.serializers import BranchSummarySerializer

from .models import Group, GroupMembership, Student


class StudentSummarySerializer(serializers.ModelSerializer):
    branch = BranchSummarySerializer(read_only=True)

    class Meta:
        model = Student
        fields = ("id", "first_name", "last_name", "branch", "status")


class StudentSerializer(serializers.ModelSerializer):
    branch = BranchSummarySerializer(read_only=True)
    branch_id = serializers.PrimaryKeyRelatedField(source="branch", queryset=Branch.objects.all(), write_only=True)
    group_ids = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = (
            "id",
            "first_name",
            "last_name",
            "date_of_birth",
            "phone",
            "email",
            "address",
            "parent_name",
            "parent_phone",
            "parent_email",
            "parent_relation",
            "branch",
            "branch_id",
            "status",
            "group_ids",
        )
        read_only_fields = ("id", "branch", "group_ids")

    def get_group_ids(self, obj):
        return [group.id for group in obj.groups.all()]

    def validate(self, attrs):
        branch = attrs.get("branch")
        if self.instance is not None and branch is not None and branch.id != self.instance.branch_id:
            raise serializers.ValidationError({"branch_id": "Student branch cannot be changed here."})
        return attrs


class GroupMembershipSerializer(serializers.ModelSerializer):
    student = StudentSummarySerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        source="student",
        queryset=Student.objects.select_related("branch").all(),
        write_only=True,
    )
    group_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = GroupMembership
        fields = ("id", "group_id", "student", "student_id", "join_date", "leave_date")
        read_only_fields = ("id", "group_id", "student", "leave_date")

    def validate(self, attrs):
        group = self.context.get("group")
        student = attrs.get("student")
        if group is not None and student.branch_id != group.branch_id:
            raise serializers.ValidationError({"student_id": "Student must belong to the same branch as the group."})
        return attrs

    def create(self, validated_data):
        group = self.context["group"]
        student = validated_data["student"]
        join_date = validated_data.get("join_date") or timezone.localdate()

        membership = group.membership_records.filter(student=student, leave_date__isnull=True).first()
        if membership is None:
            membership = GroupMembership.objects.create(group=group, student=student, join_date=join_date)
        else:
            membership.join_date = join_date
            membership.save(update_fields=["join_date"])

        group.students.add(student)
        return membership


class GroupSerializer(serializers.ModelSerializer):
    branch = BranchSummarySerializer(read_only=True)
    branch_id = serializers.PrimaryKeyRelatedField(source="branch", queryset=Branch.objects.all(), write_only=True)
    student_ids = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = (
            "id",
            "name",
            "branch",
            "branch_id",
            "status",
            "student_ids",
            "student_count",
            "memberships",
        )
        read_only_fields = ("id", "branch", "student_ids", "student_count", "memberships")

    def get_student_ids(self, obj):
        return [student.id for student in obj.students.all()]

    def get_student_count(self, obj):
        if hasattr(obj, "_prefetched_objects_cache") and "students" in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache["students"])
        return obj.students.count()

    def get_memberships(self, obj):
        memberships = obj.membership_records.all()
        return GroupMembershipSerializer(memberships, many=True).data

    def validate(self, attrs):
        branch = attrs.get("branch")
        if self.instance is not None and branch is not None and branch.id != self.instance.branch_id:
            raise serializers.ValidationError({"branch_id": "Group branch cannot be changed here."})
        return attrs
