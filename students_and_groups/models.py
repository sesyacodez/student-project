from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class StudentStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class ParentRelation(models.TextChoices):
    MOTHER = "mother", "Mother"
    FATHER = "father", "Father"
    OTHER = "other", "Other"


class GroupStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class SubscriptionPlanType(models.TextChoices):
    INDIVIDUAL = "individual", "Individual"
    GROUP = "group", "Group"


class SubscriptionPlanStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class Student(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    parent_name = models.CharField(max_length=100, blank=True)
    parent_phone = models.CharField(max_length=20, blank=True)
    parent_email = models.EmailField(blank=True)
    parent_relation = models.CharField(
        max_length=20,
        choices=ParentRelation.choices,
        blank=True,
    )
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.CASCADE,
        related_name="students",
    )
    status = models.CharField(
        max_length=20,
        choices=StudentStatus.choices,
        default=StudentStatus.ACTIVE,
    )

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Group(models.Model):
    name = models.CharField(max_length=100)
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.CASCADE,
        related_name="groups",
    )
    students = models.ManyToManyField(
        Student,
        related_name="groups",
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=GroupStatus.choices,
        default=GroupStatus.ACTIVE,
    )

    def add_student(self, student, join_date=None):
        if student.branch_id != self.branch_id:
            raise ValidationError("Student must belong to the same branch as the group.")

        join_date = join_date or timezone.localdate()
        membership = GroupMembership.objects.filter(
            group=self,
            student=student,
            leave_date__isnull=True,
        ).first()

        if membership is None:
            membership = GroupMembership.objects.create(
                group=self,
                student=student,
                join_date=join_date,
            )
        else:
            membership.join_date = join_date
            membership.save(update_fields=["join_date"])

        self.students.add(student)
        return membership

    def remove_student(self, student, leave_date=None):
        leave_date = leave_date or timezone.localdate()
        membership = GroupMembership.objects.filter(
            group=self,
            student=student,
            leave_date__isnull=True,
        ).first()

        if membership is not None:
            membership.leave_date = leave_date
            membership.save(update_fields=["leave_date"])

        self.students.remove(student)
        return membership

    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="membership_records",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="group_membership_records",
    )
    join_date = models.DateField(default=timezone.localdate)
    leave_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-join_date"]

    def __str__(self):
        return f"{self.student} in {self.group}"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.CASCADE,
        related_name="subscription_plans",
    )
    type = models.CharField(
        max_length=20,
        choices=SubscriptionPlanType.choices,
        default=SubscriptionPlanType.INDIVIDUAL,
    )
    subjects = models.ManyToManyField(
        "branches.Subject",
        related_name="subscription_plans",
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=SubscriptionPlanStatus.choices,
        default=SubscriptionPlanStatus.ACTIVE,
    )

    def __str__(self):
        return self.name


class PricingTier(models.Model):
    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name="pricing_tiers",
    )
    lessons_per_month = models.PositiveIntegerField()
    price_per_lesson = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["lessons_per_month"]
        constraints = [
            models.UniqueConstraint(
                fields=["subscription_plan", "lessons_per_month"],
                name="unique_lessons_per_month_per_plan",
            )
        ]

    def __str__(self):
        return f"{self.lessons_per_month} lessons - {self.price_per_lesson}"


class StudentSubscription(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name="student_subscriptions",
    )
    subject = models.ForeignKey(
        "branches.Subject",
        on_delete=models.CASCADE,
        related_name="student_subscriptions",
    )
    start_date = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "subscription_plan", "subject"],
                name="unique_student_plan_subject_subscription",
            )
        ]

    def clean(self):
        if self.subscription_plan_id and self.subject_id:
            if not self.subscription_plan.subjects.filter(pk=self.subject_id).exists():
                raise ValidationError(
                    {"subject": "This subject is not linked to the selected subscription plan."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.subscription_plan} - {self.subject}"
