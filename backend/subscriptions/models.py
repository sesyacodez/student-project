from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class SubscriptionPlanType(models.TextChoices):
    INDIVIDUAL = "individual", "Individual"
    GROUP = "group", "Group"


class SubscriptionPlanStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.CASCADE,
        related_name="subscription_plans",
    )
    type = models.CharField(
        max_length=20,
        choices=SubscriptionPlanType.choices,
        default=SubscriptionPlanType.INDIVIDUAL,
        db_index=True,
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
        db_index=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["branch", "type", "status"], name="subplan_branch_type_status_idx"),
        ]

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
        "students_and_groups.Student",
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
