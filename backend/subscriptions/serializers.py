from django.utils import timezone
from rest_framework import serializers

from branches.models import Branch, Subject
from branches.serializers import BranchSummarySerializer, SubjectSerializer
from students_and_groups.models import Student
from students_and_groups.serializers import StudentSummarySerializer

from .models import (
    PricingTier,
    StudentSubscription,
    SubscriptionPlan,
    SubscriptionPlanStatus,
    SubscriptionPlanType,
)


class SubscriptionPlanSummarySerializer(serializers.ModelSerializer):
    branch = BranchSummarySerializer(read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = ("id", "name", "branch", "type", "status")


class PricingTierSerializer(serializers.ModelSerializer):
    subscription_plan_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = PricingTier
        fields = ("id", "subscription_plan_id", "lessons_per_month", "price_per_lesson")

    def validate(self, attrs):
        plan = self.context.get("subscription_plan") or getattr(self.instance, "subscription_plan", None)
        lessons_per_month = attrs.get("lessons_per_month", getattr(self.instance, "lessons_per_month", None))
        if plan is not None:
            existing = plan.pricing_tiers.exclude(pk=getattr(self.instance, "pk", None)).filter(
                lessons_per_month=lessons_per_month
            )
            if existing.exists():
                raise serializers.ValidationError(
                    {"lessons_per_month": "A pricing tier with this number already exists for the plan."}
                )
        return attrs


class SubscriptionPlanReadSerializer(serializers.ModelSerializer):
    branch = BranchSummarySerializer(read_only=True)
    subject_ids = serializers.SerializerMethodField()
    subjects = SubjectSerializer(many=True, read_only=True)
    pricing_tiers = PricingTierSerializer(many=True, read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = ("id", "name", "branch", "type", "status", "subject_ids", "subjects", "pricing_tiers")

    def get_subject_ids(self, obj):
        return [subject.id for subject in obj.subjects.all()]


class SubscriptionPlanWriteSerializer(serializers.ModelSerializer):
    branch_id = serializers.PrimaryKeyRelatedField(source="branch", queryset=Branch.objects.all(), write_only=True)
    subject_ids = serializers.PrimaryKeyRelatedField(
        source="subjects",
        queryset=Subject.objects.select_related("branch").all(),
        many=True,
        required=False,
        write_only=True,
    )
    pricing_tiers = PricingTierSerializer(many=True, required=False)

    class Meta:
        model = SubscriptionPlan
        fields = ("id", "name", "branch_id", "type", "status", "subject_ids", "pricing_tiers")
        read_only_fields = ("id",)

    def validate(self, attrs):
        branch = attrs.get("branch") or getattr(self.instance, "branch", None)
        subjects = attrs.get("subjects")

        if self.instance is not None and "branch" in attrs and branch.id != self.instance.branch_id:
            raise serializers.ValidationError({"branch_id": "Subscription plan branch cannot be changed here."})

        if subjects is not None and branch is not None:
            invalid_subject_ids = [subject.id for subject in subjects if subject.branch_id != branch.id]
            if invalid_subject_ids:
                raise serializers.ValidationError(
                    {"subject_ids": "All subjects must belong to the same branch as the plan."}
                )

        return attrs

    def validate_pricing_tiers(self, value):
        seen = set()
        for tier in value:
            lessons_per_month = tier["lessons_per_month"]
            if lessons_per_month in seen:
                raise serializers.ValidationError(
                    "Duplicate lessons_per_month values are not allowed in the same plan."
                )
            seen.add(lessons_per_month)
        return value

    def _sync_subjects(self, plan, subjects):
        if subjects is not None:
            plan.subjects.set(subjects)

    def _sync_pricing_tiers(self, plan, pricing_tiers):
        if pricing_tiers is None:
            return
        plan.pricing_tiers.all().delete()
        for tier_data in pricing_tiers:
            PricingTier.objects.create(subscription_plan=plan, **tier_data)

    def create(self, validated_data):
        subjects = validated_data.pop("subjects", [])
        pricing_tiers = validated_data.pop("pricing_tiers", [])
        plan = SubscriptionPlan.objects.create(**validated_data)
        self._sync_subjects(plan, subjects)
        self._sync_pricing_tiers(plan, pricing_tiers)
        return plan

    def update(self, instance, validated_data):
        subjects = validated_data.pop("subjects", None)
        pricing_tiers = validated_data.pop("pricing_tiers", None)

        if "branch" in validated_data and validated_data["branch"].id != instance.branch_id:
            raise serializers.ValidationError({"branch_id": "Subscription plan branch cannot be changed here."})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._sync_subjects(instance, subjects)
        self._sync_pricing_tiers(instance, pricing_tiers)
        return instance


class SubscriptionPlanSubjectsSerializer(serializers.Serializer):
    subject_ids = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.select_related("branch").all(),
        many=True,
    )

    def validate_subject_ids(self, subjects):
        plan = self.context["plan"]
        invalid_subject_ids = [subject.id for subject in subjects if subject.branch_id != plan.branch_id]
        if invalid_subject_ids:
            raise serializers.ValidationError(
                {"subject_ids": "All subjects must belong to the same branch as the plan."}
            )
        return subjects

    def update(self, instance, validated_data):
        instance.subjects.set(validated_data["subject_ids"])
        return instance


class StudentSubscriptionSerializer(serializers.ModelSerializer):
    student = StudentSummarySerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        source="student",
        queryset=Student.objects.select_related("branch").all(),
        write_only=True,
    )
    subscription_plan = SubscriptionPlanSummarySerializer(read_only=True)
    subscription_plan_id = serializers.PrimaryKeyRelatedField(
        source="subscription_plan",
        queryset=SubscriptionPlan.objects.select_related("branch").prefetch_related("subjects").all(),
        write_only=True,
    )
    subject = SubjectSerializer(read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(
        source="subject",
        queryset=Subject.objects.select_related("branch").all(),
        write_only=True,
    )

    class Meta:
        model = StudentSubscription
        fields = (
            "id",
            "student",
            "student_id",
            "subscription_plan",
            "subscription_plan_id",
            "subject",
            "subject_id",
            "start_date",
        )
        read_only_fields = ("id", "student", "subscription_plan", "subject")

    def validate(self, attrs):
        student = attrs.get("student") or getattr(self.instance, "student", None)
        plan = attrs.get("subscription_plan") or getattr(self.instance, "subscription_plan", None)
        subject = attrs.get("subject") or getattr(self.instance, "subject", None)

        if plan is not None and plan.status != SubscriptionPlanStatus.ACTIVE:
            raise serializers.ValidationError(
                {"subscription_plan_id": "Archived plans cannot be assigned to new subscriptions."}
            )

        if student is not None and plan is not None and student.branch_id != plan.branch_id:
            raise serializers.ValidationError({"detail": "Student, plan, and subject must belong to the same branch."})

        if subject is not None and plan is not None and subject.branch_id != plan.branch_id:
            raise serializers.ValidationError({"detail": "Student, plan, and subject must belong to the same branch."})

        if plan is not None and subject is not None and not plan.subjects.filter(pk=subject.pk).exists():
            raise serializers.ValidationError({"subject_id": "This subject is not linked to the selected plan."})

        return attrs