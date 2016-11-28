from __future__ import unicode_literals

from django.db import migrations, models


def denormalize_pur_public_key(apps, schema_editor):
    PendingUpdateRequest = apps.get_model('index_service', 'PendingUpdateRequest')

    for pur in PendingUpdateRequest.objects.all():
        pur.public_key = pur.request['identity']['public_key']
        pur.save()


class Migration(migrations.Migration):

    dependencies = [
        ('index_service', '0006_model_translation'),
    ]

    operations = [
        migrations.AddField(
            model_name='pendingupdaterequest',
            name='public_key',
            field=models.CharField(db_index=True, default='0000000000000000000000000000000000000000000000000000000000000000', max_length=64, verbose_name='public key of request identity'),
            preserve_default=False,
        ),
        migrations.RunPython(denormalize_pur_public_key, reverse_code=lambda *args: None),
    ]
