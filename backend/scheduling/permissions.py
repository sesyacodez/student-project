"""Role helpers; viewsets still use AllowAny until JWT lands (Member 1)."""


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
