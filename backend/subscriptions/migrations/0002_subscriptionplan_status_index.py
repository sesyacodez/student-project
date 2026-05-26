from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscriptionplan",
            name="status",
            field=models.CharField(
                choices=[("active", "Active"), ("archived", "Archived")],
                db_index=True,
                default="active",
                max_length=20,
            ),
        ),
    ]
