from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from users.permissions import IsAdminRole
from .models import Branch, BranchStatus, Subject, SubjectStatus
from .serializers import BranchSerializer, SubjectSerializer

class BranchViewSet(viewsets.ModelViewSet):
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get_queryset(self):
        current_user = self.request.user
        queryset = Branch.objects.all()
        if not current_user.is_superuser:
            if current_user.branch_id:
                queryset = queryset.filter(id=current_user.branch_id)
            else:
                return Branch.objects.none()

        params = self.request.query_params
        status_value = _normalize_choice(params.get("status"), BranchStatus.values, "status")
        city = params.get("city")
        search = params.get("search")

        if status_value:
            queryset = queryset.filter(status=status_value)
        if city:
            queryset = queryset.filter(city__icontains=city)
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(address__icontains=search))

        return queryset.distinct()

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        branch = self.get_object()
        branch.status = BranchStatus.ARCHIVED
        branch.save(update_fields=["status"])
        return Response(self.get_serializer(branch).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        branch = self.get_object()
        branch.status = BranchStatus.ACTIVE
        branch.save(update_fields=["status"])
        return Response(self.get_serializer(branch).data)


def _normalize_choice(value, allowed_values, field_name):
    if value in (None, ""):
        return None
    normalized = str(value).strip().lower()
    if normalized not in allowed_values:
        raise ValidationError({field_name: f"Expected one of: {', '.join(sorted(allowed_values))}."})
    return normalized


class SubjectViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        queryset = Subject.objects.select_related("branch").order_by("name")
        params = self.request.query_params

        branch_id = params.get("branch_id")
        status_value = params.get("status")
        search = params.get("search")

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if status_value:
            queryset = queryset.filter(status=_normalize_choice(status_value, SubjectStatus.values, "status"))
        if search:
            queryset = queryset.filter(Q(name__icontains=search))

        return queryset.distinct()

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        subject = self.get_object()
        subject.status = SubjectStatus.ARCHIVED
        subject.save(update_fields=["status"])
        return Response(self.get_serializer(subject).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        subject = self.get_object()
        subject.status = SubjectStatus.ACTIVE
        subject.save(update_fields=["status"])
        return Response(self.get_serializer(subject).data)


__all__ = ["BranchViewSet", "SubjectViewSet"]