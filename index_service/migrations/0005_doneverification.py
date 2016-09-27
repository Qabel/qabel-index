from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index_service', '0004_auto_20160926_1618'),
    ]

    operations = [
        migrations.CreateModel(
            name='DoneVerification',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('id', models.CharField(max_length=36, primary_key=True, serialize=False)),
                ('state', models.CharField(choices=[('confirmed', 'Confirmed'), ('denied', 'Denied'), ('expired', 'Expired')], max_length=20)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
