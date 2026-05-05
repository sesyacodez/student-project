import json
from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from branches.models import Branch

from .models import Group, GroupStatus, Student, StudentStatus


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


def _serialize_branch(branch):
    return {"id": branch.id, "name": branch.name, "city": branch.city}


def _serialize_student(student):
    return {
        "id": student.id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "date_of_birth": student.date_of_birth.isoformat() if student.date_of_birth else None,
        "phone": student.phone,
        "email": student.email,
        "address": student.address,
        "parent_name": student.parent_name,
        "parent_phone": student.parent_phone,
        "parent_email": student.parent_email,
        "parent_relation": student.parent_relation,
        "branch": _serialize_branch(student.branch),
        "status": student.status,
        "group_ids": [group.id for group in student.groups.all()],
    }


def _serialize_membership(membership):
    return {
        "id": membership.id,
        "group_id": membership.group_id,
        "student_id": membership.student_id,
        "join_date": membership.join_date.isoformat(),
        "leave_date": membership.leave_date.isoformat() if membership.leave_date else None,
    }


def _serialize_group(group):
    memberships = [
        _serialize_membership(membership)
        for membership in group.membership_records.select_related("student").all()
    ]
    return {
        "id": group.id,
        "name": group.name,
        "branch": _serialize_branch(group.branch),
        "status": group.status,
        "student_ids": [student.id for student in group.students.all()],
        "student_count": group.students.count(),
        "memberships": memberships,
    }


def _serialize_group_student(student, membership=None):
    payload = _serialize_student(student)
    if membership is not None:
        payload["join_date"] = membership.join_date.isoformat()
        payload["leave_date"] = membership.leave_date.isoformat() if membership.leave_date else None
    return payload


def _get_student(student_id):
    return get_object_or_404(Student.objects.select_related("branch").prefetch_related("groups"), pk=student_id)


def _get_group(group_id):
    return get_object_or_404(
        Group.objects.select_related("branch").prefetch_related("students", "membership_records__student"),
        pk=group_id,
    )


def _student_queryset():
    return Student.objects.select_related("branch").prefetch_related("groups").order_by("last_name", "first_name")


def _group_queryset():
    return Group.objects.select_related("branch").prefetch_related("students", "membership_records__student").order_by("name")


def _save_student(student):
    student.full_clean()
    student.save()
    return student


def _save_group(group):
    group.full_clean()
    group.save()
    return group


@csrf_exempt
@require_http_methods(["GET", "POST"])
def student_list(request):
    if request.method == "GET":
        queryset = _student_queryset()
        branch_id = request.GET.get("branch_id")
        status = request.GET.get("status")
        group_id = request.GET.get("group_id")
        search = request.GET.get("search")

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if status:
            queryset = queryset.filter(status=_required_choice(request.GET, "status", StudentStatus.values))
        if group_id:
            queryset = queryset.filter(groups__id=group_id)
        if search:
            queryset = queryset.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search))

        return _json_response([_serialize_student(student) for student in queryset.distinct()])

    try:
        payload = _parse_payload(request)
        branch = get_object_or_404(Branch, pk=_required_int(payload, "branch_id"))
        student = Student(
            first_name=_required_text(payload, "first_name"),
            last_name=_required_text(payload, "last_name"),
            date_of_birth=_optional_date(payload, "date_of_birth"),
            phone=str(_get_value(payload, "phone", "")).strip(),
            email=str(_get_value(payload, "email", "")).strip(),
            address=str(_get_value(payload, "address", "")).strip(),
            parent_name=str(_get_value(payload, "parent_name", "")).strip(),
            parent_phone=str(_get_value(payload, "parent_phone", "")).strip(),
            parent_email=str(_get_value(payload, "parent_email", "")).strip(),
            parent_relation=str(_get_value(payload, "parent_relation", "")).strip(),
            branch=branch,
            status=_optional_choice(payload, "status", StudentStatus.values, StudentStatus.ACTIVE),
        )
        _save_student(student)
    except ValidationError as exc:
        return _validation_error_response(exc)

    return _json_response(_serialize_student(student), status=HTTPStatus.CREATED)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "PUT"])
def student_detail(request, pk):
    student = _get_student(pk)

    if request.method == "GET":
        return _json_response(_serialize_student(student))

    try:
        payload = _parse_payload(request)
        branch_id = _optional_int(payload, "branch_id")
        if branch_id is not None and branch_id != student.branch_id:
            raise ValidationError({"branch_id": "Student branch cannot be changed here."})

        if "first_name" in payload:
            student.first_name = _required_text(payload, "first_name")
        if "last_name" in payload:
            student.last_name = _required_text(payload, "last_name")
        if "date_of_birth" in payload:
            student.date_of_birth = _optional_date(payload, "date_of_birth")
        if "phone" in payload:
            student.phone = str(_get_value(payload, "phone", "")).strip()
        if "email" in payload:
            student.email = str(_get_value(payload, "email", "")).strip()
        if "address" in payload:
            student.address = str(_get_value(payload, "address", "")).strip()
        if "parent_name" in payload:
            student.parent_name = str(_get_value(payload, "parent_name", "")).strip()
        if "parent_phone" in payload:
            student.parent_phone = str(_get_value(payload, "parent_phone", "")).strip()
        if "parent_email" in payload:
            student.parent_email = str(_get_value(payload, "parent_email", "")).strip()
        if "parent_relation" in payload:
            student.parent_relation = str(_get_value(payload, "parent_relation", "")).strip()
        if "status" in payload:
            student.status = _optional_choice(payload, "status", StudentStatus.values, student.status)

        _save_student(student)
    except ValidationError as exc:
        return _validation_error_response(exc)

    return _json_response(_serialize_student(student))


@csrf_exempt
@require_http_methods(["POST"])
def student_archive(request, pk):
    student = _get_student(pk)
    student.status = StudentStatus.ARCHIVED
    _save_student(student)
    return _json_response(_serialize_student(student))


@csrf_exempt
@require_http_methods(["POST"])
def student_restore(request, pk):
    student = _get_student(pk)
    student.status = StudentStatus.ACTIVE
    _save_student(student)
    return _json_response(_serialize_student(student))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def group_list(request):
    if request.method == "GET":
        queryset = _group_queryset()
        branch_id = request.GET.get("branch_id")
        status = request.GET.get("status")
        search = request.GET.get("search")

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if status:
            queryset = queryset.filter(status=_required_choice(request.GET, "status", GroupStatus.values))
        if search:
            queryset = queryset.filter(name__icontains=search)

        return _json_response([_serialize_group(group) for group in queryset.distinct()])

    try:
        payload = _parse_payload(request)
        branch = get_object_or_404(Branch, pk=_required_int(payload, "branch_id"))
        group = Group(
            name=_required_text(payload, "name"),
            branch=branch,
            status=_optional_choice(payload, "status", GroupStatus.values, GroupStatus.ACTIVE),
        )
        _save_group(group)
    except ValidationError as exc:
        return _validation_error_response(exc)

    return _json_response(_serialize_group(group), status=HTTPStatus.CREATED)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "PUT"])
def group_detail(request, pk):
    group = _get_group(pk)

    if request.method == "GET":
        return _json_response(_serialize_group(group))

    try:
        payload = _parse_payload(request)
        branch_id = _optional_int(payload, "branch_id")
        if branch_id is not None and branch_id != group.branch_id:
            raise ValidationError({"branch_id": "Group branch cannot be changed here."})

        if "name" in payload:
            group.name = _required_text(payload, "name")
        if "status" in payload:
            group.status = _optional_choice(payload, "status", GroupStatus.values, group.status)

        _save_group(group)
    except ValidationError as exc:
        return _validation_error_response(exc)

    return _json_response(_serialize_group(group))


@csrf_exempt
@require_http_methods(["POST"])
def group_archive(request, pk):
    group = _get_group(pk)
    group.status = GroupStatus.ARCHIVED
    _save_group(group)
    return _json_response(_serialize_group(group))


@csrf_exempt
@require_http_methods(["POST"])
def group_restore(request, pk):
    group = _get_group(pk)
    group.status = GroupStatus.ACTIVE
    _save_group(group)
    return _json_response(_serialize_group(group))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def group_students(request, pk):
    group = _get_group(pk)

    if request.method == "GET":
        memberships = {
            membership.student_id: membership
            for membership in group.membership_records.filter(leave_date__isnull=True).select_related("student")
        }
        students = []
        for student in group.students.order_by("last_name", "first_name"):
            students.append(_serialize_group_student(student, memberships.get(student.id)))
        return _json_response(students)

    try:
        payload = _parse_payload(request)
        student = _get_student(_required_int(payload, "student_id"))
        join_date = _optional_date(payload, "join_date")
        membership = group.add_student(student, join_date=join_date)
    except ValidationError as exc:
        return _validation_error_response(exc)

    if membership is not None:
        membership.refresh_from_db()
    return _json_response(
        {
            "group": _serialize_group(group),
            "student": _serialize_student(student),
            "membership": _serialize_membership(membership) if membership is not None else None,
        },
        status=HTTPStatus.CREATED,
    )


@csrf_exempt
@require_http_methods(["DELETE"])
def group_student_remove(request, pk, student_id):
    group = _get_group(pk)
    student = _get_student(student_id)

    membership = group.remove_student(student)
    return _json_response(
        {
            "group": _serialize_group(group),
            "student": _serialize_student(student),
            "membership": _serialize_membership(membership) if membership is not None else None,
            "removed": membership is not None,
        }
    )