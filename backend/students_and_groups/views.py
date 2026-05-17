from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Group, GroupMembership, GroupStatus, Student, StudentStatus
from .serializers import GroupMembershipSerializer, GroupSerializer, StudentSerializer


def _normalize_choice(value, allowed_values, field_name):
	if value in (None, ""):
		return None
	normalized = str(value).strip().lower()
	if normalized not in allowed_values:
		raise ValidationError({field_name: f"Expected one of: {', '.join(sorted(allowed_values))}."})
	return normalized


class StudentViewSet(viewsets.ModelViewSet):
	serializer_class = StudentSerializer
	permission_classes = [AllowAny]
	authentication_classes = []

	def get_queryset(self):
		queryset = Student.objects.select_related("branch").prefetch_related("groups").order_by("last_name", "first_name")
		params = self.request.query_params

		branch_id = params.get("branch_id")
		status_value = _normalize_choice(params.get("status"), StudentStatus.values, "status")
		group_id = params.get("group_id")
		search = params.get("search")

		if branch_id:
			queryset = queryset.filter(branch_id=branch_id)
		if status_value:
			queryset = queryset.filter(status=status_value)
		if group_id:
			queryset = queryset.filter(groups__id=group_id)
		if search:
			queryset = queryset.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search))

		return queryset.distinct()

	@action(detail=True, methods=["post"])
	def archive(self, request, pk=None):
		student = self.get_object()
		student.status = StudentStatus.ARCHIVED
		student.save(update_fields=["status"])
		return Response(self.get_serializer(student).data)

	@action(detail=True, methods=["post"])
	def restore(self, request, pk=None):
		student = self.get_object()
		student.status = StudentStatus.ACTIVE
		student.save(update_fields=["status"])
		return Response(self.get_serializer(student).data)


class GroupViewSet(viewsets.ModelViewSet):
	serializer_class = GroupSerializer
	permission_classes = [AllowAny]
	authentication_classes = []

	def get_queryset(self):
		membership_queryset = GroupMembership.objects.select_related("student", "student__branch").order_by("-join_date")
		queryset = Group.objects.select_related("branch").prefetch_related(
			"students",
			Prefetch("membership_records", queryset=membership_queryset),
		).order_by("name")
		params = self.request.query_params

		branch_id = params.get("branch_id")
		status_value = _normalize_choice(params.get("status"), GroupStatus.values, "status")
		search = params.get("search")

		if branch_id:
			queryset = queryset.filter(branch_id=branch_id)
		if status_value:
			queryset = queryset.filter(status=status_value)
		if search:
			queryset = queryset.filter(name__icontains=search)

		return queryset.distinct()

	@action(detail=True, methods=["post"])
	def archive(self, request, pk=None):
		group = self.get_object()
		group.status = GroupStatus.ARCHIVED
		group.save(update_fields=["status"])
		return Response(self.get_serializer(group).data)

	@action(detail=True, methods=["post"])
	def restore(self, request, pk=None):
		group = self.get_object()
		group.status = GroupStatus.ACTIVE
		group.save(update_fields=["status"])
		return Response(self.get_serializer(group).data)

	@action(detail=True, methods=["get", "post"])
	def students(self, request, pk=None):
		group = self.get_object()
		if request.method == "GET":
			memberships = group.membership_records.filter(leave_date__isnull=True).select_related("student", "student__branch").order_by("join_date")
			serializer = GroupMembershipSerializer(memberships, many=True)
			return Response(serializer.data)

		serializer = GroupMembershipSerializer(data=request.data, context={"group": group})
		serializer.is_valid(raise_exception=True)
		membership = serializer.save()
		return Response(GroupMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

	@action(detail=True, methods=["delete"], url_path=r"students/(?P<student_id>[^/.]+)")
	def remove_student(self, request, pk=None, student_id=None):
		group = self.get_object()
		student = get_object_or_404(Student.objects.select_related("branch"), pk=student_id)
		if student.branch_id != group.branch_id:
			raise ValidationError({"student_id": "Student must belong to the same branch as the group."})

		membership = group.membership_records.filter(student=student, leave_date__isnull=True).first()
		if membership is not None:
			membership.leave_date = timezone.localdate()
			membership.save(update_fields=["leave_date"])

		group.students.remove(student)
		return Response({"removed": membership is not None})