import json
from decimal import Decimal, InvalidOperation
from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from branches.models import Branch, Subject
from students_and_groups.models import Student

from .models import (
    PricingTier,
    StudentSubscription,
    SubscriptionPlan,
    SubscriptionPlanStatus,
    SubscriptionPlanType,
)


def _json_response(data, status=HTTPStatus.OK):
    return JsonResponse(
        data,
        status=status,
        safe=not isinstance(data, list),
        json_dumps_params={"ensure_ascii": False},
    )


def _json_error(detail, status=HTTPStatus.BAD_REQUEST, errors=None):
    payload = {"detail": detail}
    if errors is not None:
        payload["errors"] = errors
    return _json_response(payload, status=status)


def _validation_error_response(exc):
    if hasattr(exc, "message_dict"):
        return _json_error("Validation failed.", errors=exc.message_dict)
    return _json_error("Validation failed.", errors={"detail": exc.messages})


def _parse_payload(request):
    content_type = request.headers.get("Content-Type", "")
    if "application/json" in content_type:
        if not request.body:
            return {}
        try:
            return json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError({"detail": "Invalid JSON payload."}) from exc

    return request.POST


def _get_value(payload, key, default=None):
    if hasattr(payload, "getlist"):
        values = payload.getlist(key)
        if len(values) > 1:
            return values
        if len(values) == 1:
            return values[0]
        return default
    return payload.get(key, default)


def _required_text(payload, key):
    value = _get_value(payload, key)
    if value is None or str(value).strip() == "":
        raise ValidationError({key: "This field is required."})
    return str(value).strip()


def _required_int(payload, key):
    value = _get_value(payload, key)
    if value is None or str(value).strip() == "":
        raise ValidationError({key: "This field is required."})
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({key: "A valid integer is required."}) from exc


def _optional_int(payload, key):
    value = _get_value(payload, key)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({key: "A valid integer is required."}) from exc


def _required_decimal(payload, key):
    value = _required_text(payload, key)
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError({key: "Enter a valid decimal value."}) from exc


def _required_choice(payload, key, allowed_values):
    value = _required_text(payload, key).lower()
    if value not in allowed_values:
        raise ValidationError({key: f"Expected one of: {', '.join(sorted(allowed_values))}."})
    return value


def _optional_choice(payload, key, allowed_values, default):
    value = _get_value(payload, key)
    if value in (None, ""):
        return default
    value = str(value).strip().lower()
    if value not in allowed_values:
        raise ValidationError({key: f"Expected one of: {', '.join(sorted(allowed_values))}."})
    return value


def _optional_date(payload, key):
    value = _get_value(payload, key)
    if value in (None, ""):
        return None
    parsed = parse_date(str(value))
    if parsed is None:
        raise ValidationError({key: "Enter a valid date in YYYY-MM-DD format."})
    return parsed


def _as_int_list(value, key):
    if value in (None, ""):
        return []
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        if value.startswith("["):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValidationError({key: "Enter a valid list of integers."}) from exc
        else:
            value = [item.strip() for item in value.split(",") if item.strip()]

    if not isinstance(value, (list, tuple, set)):
        value = [value]

    result = []
    for item in value:
        try:
            result.append(int(item))
        except (TypeError, ValueError) as exc:
            raise ValidationError({key: "Enter a valid list of integers."}) from exc
    return result


def _serialize_branch(branch):
    return {"id": branch.id, "name": branch.name, "city": branch.city}


def _serialize_subject(subject):
    return {
        "id": subject.id,
        "name": subject.name,
        "branch": _serialize_branch(subject.branch),
        "status": subject.status,
    }


def _serialize_pricing_tier(tier):
    return {
        "id": tier.id,
        "subscription_plan_id": tier.subscription_plan_id,
        "lessons_per_month": tier.lessons_per_month,
        "price_per_lesson": str(tier.price_per_lesson),
    }


def _serialize_plan(plan):
    return {
        "id": plan.id,
        "name": plan.name,
        "branch": _serialize_branch(plan.branch),
        "type": plan.type,
        "status": plan.status,
        "subject_ids": [subject.id for subject in plan.subjects.all()],
        "subjects": [_serialize_subject(subject) for subject in plan.subjects.all()],
        "pricing_tiers": [
            _serialize_pricing_tier(tier)
            for tier in plan.pricing_tiers.all().order_by("lessons_per_month")
        ],
    }


def _serialize_student_short(student):
    return {
        "id": student.id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "branch": _serialize_branch(student.branch),
        "status": student.status,
    }


def _serialize_subscription(subscription):
    return {
        "id": subscription.id,
        "student": _serialize_student_short(subscription.student),
        "subscription_plan": {
            "id": subscription.subscription_plan.id,
            "name": subscription.subscription_plan.name,
            "type": subscription.subscription_plan.type,
            "status": subscription.subscription_plan.status,
            "branch": _serialize_branch(subscription.subscription_plan.branch),
        },
        "subject": _serialize_subject(subscription.subject),
        "start_date": subscription.start_date.isoformat(),
    }


def _get_plan(plan_id):
    return get_object_or_404(
        SubscriptionPlan.objects.select_related("branch").prefetch_related("subjects", "pricing_tiers"),
        pk=plan_id,
    )


def _get_tier(tier_id):
    return get_object_or_404(PricingTier.objects.select_related("subscription_plan"), pk=tier_id)


def _get_subscription(subscription_id):
    return get_object_or_404(
        StudentSubscription.objects.select_related(
            "student__branch",
            "subscription_plan__branch",
            "subject__branch",
        ),
        pk=subscription_id,
    )


def _save_plan(plan):
    plan.full_clean()
    plan.save()
    return plan


def _save_tier(tier):
    tier.full_clean()
    tier.save()
    return tier


def _save_subscription(subscription):
    subscription.save()
    return subscription


def _validate_plan_subjects(plan, subject_ids):
    if not subject_ids:
        return []

    subjects = list(Subject.objects.select_related("branch").filter(pk__in=subject_ids))
    found_ids = {subject.id for subject in subjects}
    missing_ids = [subject_id for subject_id in subject_ids if subject_id not in found_ids]
    if missing_ids:
        raise ValidationError({"subject_ids": f"Unknown subject ids: {missing_ids}."})
    if any(subject.branch_id != plan.branch_id for subject in subjects):
        raise ValidationError({"subject_ids": "All subjects must belong to the same branch as the plan."})
    return subjects


def _validate_plan_tiers(tiers_payload):
    if tiers_payload in (None, ""):
        return []
    if not isinstance(tiers_payload, list):
        raise ValidationError({"pricing_tiers": "Enter a list of pricing tier objects."})

    tiers = []
    for index, tier_payload in enumerate(tiers_payload):
        if not isinstance(tier_payload, dict):
            raise ValidationError({"pricing_tiers": f"Item {index} must be an object."})
        tiers.append(
            {
                "lessons_per_month": _required_int(tier_payload, "lessons_per_month"),
                "price_per_lesson": _required_decimal(tier_payload, "price_per_lesson"),
            }
        )
    return tiers


@csrf_exempt
@require_http_methods(["GET", "POST"])
def subscription_plan_list(request):
    if request.method == "GET":
        queryset = SubscriptionPlan.objects.select_related("branch").prefetch_related("subjects", "pricing_tiers").order_by("name")
        branch_id = request.GET.get("branch_id")
        plan_type = request.GET.get("type")
        status = request.GET.get("status")
        search = request.GET.get("search")

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if plan_type:
            queryset = queryset.filter(type=_required_choice(request.GET, "type", SubscriptionPlanType.values))
        if status:
            queryset = queryset.filter(status=_required_choice(request.GET, "status", SubscriptionPlanStatus.values))
        if search:
            queryset = queryset.filter(name__icontains=search)

        return _json_response([_serialize_plan(plan) for plan in queryset.distinct()])

    try:
        payload = _parse_payload(request)
        branch = get_object_or_404(Branch, pk=_required_int(payload, "branch_id"))
        subject_ids = _as_int_list(_get_value(payload, "subject_ids", []), "subject_ids")
        tiers_payload = _get_value(payload, "pricing_tiers", [])

        with transaction.atomic():
            plan = SubscriptionPlan(
                name=_required_text(payload, "name"),
                branch=branch,
                type=_optional_choice(payload, "type", SubscriptionPlanType.values, SubscriptionPlanType.INDIVIDUAL),
                status=_optional_choice(payload, "status", SubscriptionPlanStatus.values, SubscriptionPlanStatus.ACTIVE),
            )
            _save_plan(plan)

            subjects = _validate_plan_subjects(plan, subject_ids)
            if subjects:
                plan.subjects.set(subjects)

            for tier_payload in _validate_plan_tiers(tiers_payload):
                tier = PricingTier(
                    subscription_plan=plan,
                    lessons_per_month=tier_payload["lessons_per_month"],
                    price_per_lesson=tier_payload["price_per_lesson"],
                )
                _save_tier(tier)
    except ValidationError as exc:
        return _validation_error_response(exc)

    plan.refresh_from_db()
    return _json_response(_serialize_plan(plan), status=HTTPStatus.CREATED)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "PUT"])
def subscription_plan_detail(request, pk):
    plan = _get_plan(pk)

    if request.method == "GET":
        return _json_response(_serialize_plan(plan))

    try:
        payload = _parse_payload(request)
        branch_id = _optional_int(payload, "branch_id")
        if branch_id is not None and branch_id != plan.branch_id:
            raise ValidationError({"branch_id": "Subscription plan branch cannot be changed here."})

        if "name" in payload:
            plan.name = _required_text(payload, "name")
        if "type" in payload:
            plan.type = _optional_choice(payload, "type", SubscriptionPlanType.values, plan.type)
        if "status" in payload:
            plan.status = _optional_choice(payload, "status", SubscriptionPlanStatus.values, plan.status)

        _save_plan(plan)
    except ValidationError as exc:
        return _validation_error_response(exc)

    plan.refresh_from_db()
    return _json_response(_serialize_plan(plan))


@csrf_exempt
@require_http_methods(["POST"])
def subscription_plan_archive(request, pk):
    plan = _get_plan(pk)
    plan.status = SubscriptionPlanStatus.ARCHIVED
    _save_plan(plan)
    plan.refresh_from_db()
    return _json_response(_serialize_plan(plan))


@csrf_exempt
@require_http_methods(["POST"])
def subscription_plan_restore(request, pk):
    plan = _get_plan(pk)
    plan.status = SubscriptionPlanStatus.ACTIVE
    _save_plan(plan)
    plan.refresh_from_db()
    return _json_response(_serialize_plan(plan))


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def subscription_plan_subjects(request, pk):
    plan = _get_plan(pk)

    if request.method == "GET":
        subjects = plan.subjects.select_related("branch").order_by("name")
        return _json_response([_serialize_subject(subject) for subject in subjects])

    try:
        payload = _parse_payload(request)
        if "subject_ids" not in payload:
            raise ValidationError({"subject_ids": "This field is required."})
        subject_ids = _as_int_list(_get_value(payload, "subject_ids"), "subject_ids")
        subjects = _validate_plan_subjects(plan, subject_ids)
        plan.subjects.set(subjects)
    except ValidationError as exc:
        return _validation_error_response(exc)

    return _json_response({"subject_ids": [subject.id for subject in plan.subjects.all()]})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def subscription_plan_pricing_tiers(request, pk):
    plan = _get_plan(pk)

    if request.method == "GET":
        tiers = plan.pricing_tiers.all().order_by("lessons_per_month")
        return _json_response([_serialize_pricing_tier(tier) for tier in tiers])

    try:
        payload = _parse_payload(request)
        tier = PricingTier(
            subscription_plan=plan,
            lessons_per_month=_required_int(payload, "lessons_per_month"),
            price_per_lesson=_required_decimal(payload, "price_per_lesson"),
        )
        _save_tier(tier)
    except ValidationError as exc:
        return _validation_error_response(exc)

    return _json_response(_serialize_pricing_tier(tier), status=HTTPStatus.CREATED)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
def pricing_tier_detail(request, pk):
    tier = _get_tier(pk)

    if request.method == "GET":
        return _json_response(_serialize_pricing_tier(tier))

    if request.method == "DELETE":
        tier.delete()
        return _json_response({"detail": "Pricing tier deleted."})

    try:
        payload = _parse_payload(request)
        if "lessons_per_month" in payload:
            tier.lessons_per_month = _required_int(payload, "lessons_per_month")
        if "price_per_lesson" in payload:
            tier.price_per_lesson = _required_decimal(payload, "price_per_lesson")
        _save_tier(tier)
    except ValidationError as exc:
        return _validation_error_response(exc)

    return _json_response(_serialize_pricing_tier(tier))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def student_subscription_list(request):
    if request.method == "GET":
        queryset = (
            StudentSubscription.objects.select_related(
                "student__branch",
                "subscription_plan__branch",
                "subject__branch",
            )
            .prefetch_related("subscription_plan__subjects", "subscription_plan__pricing_tiers")
            .order_by("-start_date")
        )
        student_id = request.GET.get("student_id")
        subject_id = request.GET.get("subject_id")
        subscription_plan_id = request.GET.get("subscription_plan_id")
        branch_id = request.GET.get("branch_id")
        search = request.GET.get("search")

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

        return _json_response([_serialize_subscription(subscription) for subscription in queryset.distinct()])

    try:
        payload = _parse_payload(request)
        student = get_object_or_404(Student.objects.select_related("branch"), pk=_required_int(payload, "student_id"))
        plan = _get_plan(_required_int(payload, "subscription_plan_id"))
        subject = get_object_or_404(Subject.objects.select_related("branch"), pk=_required_int(payload, "subject_id"))
        start_date = _optional_date(payload, "start_date") or timezone.localdate()

        if plan.status != SubscriptionPlanStatus.ACTIVE:
            raise ValidationError({"subscription_plan_id": "Archived plans cannot be assigned to new subscriptions."})
        if student.branch_id != plan.branch_id or subject.branch_id != plan.branch_id:
            raise ValidationError({"detail": "Student, plan, and subject must belong to the same branch."})
        if not plan.subjects.filter(pk=subject.pk).exists():
            raise ValidationError({"subject_id": "This subject is not linked to the selected plan."})

        subscription = StudentSubscription(
            student=student,
            subscription_plan=plan,
            subject=subject,
            start_date=start_date,
        )
        _save_subscription(subscription)
    except ValidationError as exc:
        return _validation_error_response(exc)

    subscription.refresh_from_db()
    return _json_response(_serialize_subscription(subscription), status=HTTPStatus.CREATED)


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def student_subscription_detail(request, pk):
    subscription = _get_subscription(pk)

    if request.method == "GET":
        return _json_response(_serialize_subscription(subscription))

    try:
        payload = _parse_payload(request)

        if "student_id" in payload:
            subscription.student = get_object_or_404(
                Student.objects.select_related("branch"),
                pk=_required_int(payload, "student_id"),
            )
        if "subscription_plan_id" in payload:
            subscription.subscription_plan = _get_plan(_required_int(payload, "subscription_plan_id"))
        if "subject_id" in payload:
            subscription.subject = get_object_or_404(
                Subject.objects.select_related("branch"),
                pk=_required_int(payload, "subject_id"),
            )
        if "start_date" in payload:
            subscription.start_date = _optional_date(payload, "start_date") or subscription.start_date

        if subscription.subscription_plan.status != SubscriptionPlanStatus.ACTIVE:
            raise ValidationError({"subscription_plan_id": "Archived plans cannot be assigned to subscriptions."})
        if (
            subscription.student.branch_id != subscription.subscription_plan.branch_id
            or subscription.subject.branch_id != subscription.subscription_plan.branch_id
        ):
            raise ValidationError({"detail": "Student, plan, and subject must belong to the same branch."})
        if not subscription.subscription_plan.subjects.filter(pk=subscription.subject_id).exists():
            raise ValidationError({"subject_id": "This subject is not linked to the selected plan."})

        _save_subscription(subscription)
    except ValidationError as exc:
        return _validation_error_response(exc)

    subscription.refresh_from_db()
    return _json_response(_serialize_subscription(subscription))