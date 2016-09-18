from __future__ import unicode_literals

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('index_service', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='entry',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=timezone.now()),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='identity',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=timezone.now()),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='pendingupdaterequest',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=timezone.now()),
            preserve_default=False,
        ),
    ]
