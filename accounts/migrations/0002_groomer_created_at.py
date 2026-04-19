from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='groomer',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
