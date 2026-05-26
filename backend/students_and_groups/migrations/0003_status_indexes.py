from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("students_and_groups", "0002_remove_groupmembership_unique_group_student_membership"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="status",
            field=models.CharField(
                choices=[("active", "Active"), ("archived", "Archived")],
                db_index=True,
                default="active",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="group",
            name="status",
            field=models.CharField(
                choices=[("active", "Active"), ("archived", "Archived")],
                db_index=True,
                default="active",
                max_length=20,
            ),
        ),
    ]
