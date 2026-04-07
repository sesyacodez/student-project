from django.db import models


class BranchStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class SubjectStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class Branch(models.Model):
    name = models.CharField(max_length=255, verbose_name="Branch Name")
    address = models.CharField(max_length=255, verbose_name="Address")
    city = models.CharField(max_length=100, verbose_name="City")
    status = models.CharField(
        max_length=20,
        choices=BranchStatus.choices,
        default=BranchStatus.ACTIVE,
        verbose_name="Status",
    )

    def archive(self):
        self.status = BranchStatus.ARCHIVED
        self.save()

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class Subject(models.Model):
    name = models.CharField(max_length=100)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="subjects",
    )
    status = models.CharField(
        max_length=20,
        choices=SubjectStatus.choices,
        default=SubjectStatus.ACTIVE,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                name="unique_subject_name_per_branch",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.branch})"