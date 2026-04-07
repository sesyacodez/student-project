from django.db import models

class Branch(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
    )

    name = models.CharField(max_length=255, verbose_name="Branch Name")
    address = models.CharField(max_length=255, verbose_name="Address")
    city = models.CharField(max_length=100, verbose_name="City")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE', verbose_name="Status")

    def archive(self):
        self.status = 'ARCHIVED'
        self.save()

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"