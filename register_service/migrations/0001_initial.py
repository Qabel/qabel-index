# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Identity',
            fields=[
                ('alias', models.CharField(max_length=255, db_index=True)),
                ('public_key', models.TextField(serialize=False, primary_key=True, db_index=True)),
                ('drop_url', models.URLField()),
                ('email', models.EmailField(db_index=True, max_length=254, blank=True)),
                ('mobile', phonenumber_field.modelfields.PhoneNumberField(db_index=True, max_length=128, blank=True)),
                ('created_at', models.DateTimeField(editable=False)),
                ('updated_at', models.DateTimeField()),
            ],
        ),
    ]
