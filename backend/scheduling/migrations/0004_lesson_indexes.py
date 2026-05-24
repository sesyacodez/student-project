import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0003_alter_lesson_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lesson",
            name="date",
            field=models.DateField(db_index=True),
        ),
        migrations.AlterField(
            model_name="lesson",
            name="status",
            field=models.CharField(
                choices=[
                    ("scheduled", "Scheduled"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                ],
                db_index=True,
                default="scheduled",
                max_length=9,
            ),
        ),
        migrations.AlterField(
            model_name="lesson",
            name="student",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="lessons",
                to="students_and_groups.student",
            ),
        ),
        migrations.AlterField(
            model_name="lesson",
            name="group",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name="lessons",
                to="students_and_groups.group",
            ),
        ),
        migrations.AddIndex(
            model_name="lesson",
            index=models.Index(
                fields=["date", "start_time", "end_time"],
                name="lesson_date_time_idx",
            ),
        ),
    ]
