from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import PricingTier, StudentSubscription, SubscriptionPlan, SubscriptionPlanStatus, SubscriptionPlanType
from .serializers import (
	PricingTierSerializer,
	StudentSubscriptionSerializer,
	SubscriptionPlanReadSerializer,
	SubscriptionPlanSubjectsSerializer,
	SubscriptionPlanWriteSerializer,
)


def _normalize_choice(value, allowed_values, field_name):
	if value in (None, ""):
		return None
	normalized = str(value).strip().lower()
	if normalized not in allowed_values:
		raise ValidationError({field_name: f"Expected one of: {', '.join(sorted(allowed_values))}."})
	return normalized


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
	permission_classes = [AllowAny]
	authentication_classes = []

	def get_queryset(self):
		queryset = SubscriptionPlan.objects.select_related("branch").prefetch_related("subjects", "pricing_tiers").order_by("name")
		params = self.request.query_params

		branch_id = params.get("branch_id")
		plan_type = _normalize_choice(params.get("type"), SubscriptionPlanType.values, "type")
		status_value = _normalize_choice(params.get("status"), SubscriptionPlanStatus.values, "status")
		search = params.get("search")

		if branch_id:
			queryset = queryset.filter(branch_id=branch_id)
		if plan_type:
			queryset = queryset.filter(type=plan_type)
		if status_value:
			queryset = queryset.filter(status=status_value)
		if search:
			queryset = queryset.filter(name__icontains=search)

		return queryset.distinct()

	def get_serializer_class(self):
		if self.action in {"create", "update", "partial_update"}:
			return SubscriptionPlanWriteSerializer
		return SubscriptionPlanReadSerializer

	def _serialize_plan(self, plan):
		return SubscriptionPlanReadSerializer(plan, context=self.get_serializer_context()).data

	def create(self, request, *args, **kwargs):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		plan = serializer.save()
		return Response(self._serialize_plan(plan), status=status.HTTP_201_CREATED)

	def update(self, request, *args, **kwargs):
		partial = kwargs.pop("partial", False)
		instance = self.get_object()
		serializer = self.get_serializer(instance, data=request.data, partial=partial)
		serializer.is_valid(raise_exception=True)
		plan = serializer.save()
		return Response(self._serialize_plan(plan))

	@action(detail=True, methods=["post"])
	def archive(self, request, pk=None):
		plan = self.get_object()
		plan.status = SubscriptionPlanStatus.ARCHIVED
		plan.save(update_fields=["status"])
		return Response(self._serialize_plan(plan))

	@action(detail=True, methods=["post"])
	def restore(self, request, pk=None):
		plan = self.get_object()
		plan.status = SubscriptionPlanStatus.ACTIVE
		plan.save(update_fields=["status"])
		return Response(self._serialize_plan(plan))

	@action(detail=True, methods=["get", "put"])
	def subjects(self, request, pk=None):
		plan = self.get_object()
		if request.method == "GET":
			subjects = plan.subjects.select_related("branch").order_by("name")
			return Response(SubscriptionPlanReadSerializer(plan, context=self.get_serializer_context()).data["subjects"])

		serializer = SubscriptionPlanSubjectsSerializer(instance=plan, data=request.data, context={"plan": plan})
		serializer.is_valid(raise_exception=True)
		plan = serializer.save()
		return Response(self._serialize_plan(plan))

	@action(detail=True, methods=["get", "post"])
	def pricing_tiers(self, request, pk=None):
		plan = self.get_object()
		if request.method == "GET":
			tiers = plan.pricing_tiers.all().order_by("lessons_per_month")
			return Response(PricingTierSerializer(tiers, many=True, context=self.get_serializer_context()).data)

		serializer = PricingTierSerializer(data=request.data, context={"subscription_plan": plan})
		serializer.is_valid(raise_exception=True)
		tier = serializer.save(subscription_plan=plan)
		return Response(PricingTierSerializer(tier, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)


class PricingTierViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
	serializer_class = PricingTierSerializer
	permission_classes = [AllowAny]
	authentication_classes = []

	def get_queryset(self):
		return PricingTier.objects.select_related("subscription_plan__branch").order_by("subscription_plan_id", "lessons_per_month")


class StudentSubscriptionViewSet(viewsets.ModelViewSet):
	serializer_class = StudentSubscriptionSerializer
	permission_classes = [AllowAny]
	authentication_classes = []

	def get_queryset(self):
		queryset = (
			StudentSubscription.objects.select_related(
				"student__branch",
				"subscription_plan__branch",
				"subject__branch",
			)
			.prefetch_related("subscription_plan__subjects", "subscription_plan__pricing_tiers")
			.order_by("-start_date")
		)
		params = self.request.query_params

		student_id = params.get("student_id")
		subject_id = params.get("subject_id")
		subscription_plan_id = params.get("subscription_plan_id")
		branch_id = params.get("branch_id")
		search = params.get("search")

		if student_id:
			queryset = queryset.filter(student_id=student_id)
		if subject_id:
			queryset = queryset.filter(subject_id=subject_id)
		if subscription_plan_id:
			queryset = queryset.filter(subscription_plan_id=subscription_plan_id)
		if branch_id:
			queryset = queryset.filter(student__branch_id=branch_id)
		if search:
			queryset = queryset.filter(
				Q(student__first_name__icontains=search)
				| Q(student__last_name__icontains=search)
				| Q(subject__name__icontains=search)
				| Q(subscription_plan__name__icontains=search)
			)

		return queryset.distinct()