from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_phoneotp_alter_customuser_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='driverprofile',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
    ]
