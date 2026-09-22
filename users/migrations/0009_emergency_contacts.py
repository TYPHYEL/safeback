from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_driverprofile_face_embedding_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmergencyContact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('phone', models.CharField(max_length=32)),
                ('relation', models.CharField(choices=[('parent', 'Parent'), ('sibling', 'Frere/Soeur'), ('spouse', 'Conjoint(e)'), ('child', 'Enfant'), ('friend', 'Ami(e)'), ('colleague', 'Collegue'), ('other', 'Autre')], default='other', max_length=20)),
                ('can_receive_sms', models.BooleanField(default=True)),
                ('can_receive_call', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='emergency_contacts', to='users.customuser')),
            ],
        ),
    ]
