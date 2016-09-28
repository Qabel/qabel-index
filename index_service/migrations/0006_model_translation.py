from __future__ import unicode_literals

from django.db import migrations, models

# None of this *should* actually touch the DDL.


class Migration(migrations.Migration):

    dependencies = [
        ('index_service', '0005_doneverification'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='doneverification',
            options={'verbose_name': 'done verification model', 'verbose_name_plural': 'done verification model plural'},
        ),
        migrations.AlterModelOptions(
            name='entry',
            options={'verbose_name': 'entry model', 'verbose_name_plural': 'entries model plural'},
        ),
        migrations.AlterModelOptions(
            name='identity',
            options={'verbose_name': 'identity model', 'verbose_name_plural': 'identities model plural'},
        ),
        migrations.AlterModelOptions(
            name='pendingupdaterequest',
            options={'verbose_name': 'pending update request model', 'verbose_name_plural': 'pending update request model plural'},
        ),
        migrations.AlterModelOptions(
            name='pendingverification',
            options={'verbose_name': 'pending verification model', 'verbose_name_plural': 'pending verification model plural'},
        ),
        migrations.AlterField(
            model_name='doneverification',
            name='created',
            field=models.DateTimeField(auto_now_add=True, verbose_name='creation timestamp field'),
        ),
        migrations.AlterField(
            model_name='entry',
            name='created',
            field=models.DateTimeField(auto_now_add=True, verbose_name='creation timestamp field'),
        ),
        migrations.AlterField(
            model_name='identity',
            name='created',
            field=models.DateTimeField(auto_now_add=True, verbose_name='creation timestamp field'),
        ),
        migrations.AlterField(
            model_name='pendingupdaterequest',
            name='created',
            field=models.DateTimeField(auto_now_add=True, verbose_name='creation timestamp field'),
        ),
    ]
