from rest_framework.permissions import BasePermission


def is_teacher_user(user):
    return bool(
        user
        and user.is_authenticated
        and getattr(user, "role", None) == "TEACHER"
    )


def is_admin_user(user):
    return bool(
        user
        and user.is_authenticated
        and getattr(user, "role", None) == "ADMIN"
    )


class IsAdminUserRole(BasePermission):
    message = "Administrator role required."

    def has_permission(self, request, view):
        return is_admin_user(request.user)


class IsAdminOrTeacherUserRole(BasePermission):
    message = "Administrator or teacher role required."

    def has_permission(self, request, view):
        return is_admin_user(request.user) or is_teacher_user(request.user)


class IsAdminOrLessonTeacher(BasePermission):
    message = "You can only access your own lessons."

    def has_permission(self, request, view):
        return is_admin_user(request.user) or is_teacher_user(request.user)

    def has_object_permission(self, request, view, obj):
        if is_admin_user(request.user):
            return True

        lesson_teacher_id = getattr(obj, "teacher_id", None)
        if lesson_teacher_id is None and hasattr(obj, "lesson"):
            lesson_teacher_id = getattr(obj.lesson, "teacher_id", None)

        return (
            is_teacher_user(request.user)
            and lesson_teacher_id == request.user.pk
        )
