from __future__ import unicode_literals

from django.db import migrations


def delete_violating_rows(apps, schema_editor):
    Entry = apps.get_model('index_service', 'Entry')
    for entry in Entry.objects.all():
        duplicates = Entry.objects.filter(field=entry.field, identity=entry.identity)
        if duplicates.count() > 1:
            duplicates.exclude(id=entry.id).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('index_service', '0002_add_creation_timestamps'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='entry',
            options={'verbose_name_plural': 'Entries'},
        ),
        migrations.AlterModelOptions(
            name='identity',
            options={'verbose_name_plural': 'Identities'},
        ),
        migrations.RunPython(delete_violating_rows),
        migrations.AlterUniqueTogether(
            name='entry',
            unique_together=set([('field', 'identity')]),
        ),
        migrations.AlterIndexTogether(
            name='entry',
            index_together=set([('field', 'identity')]),
        ),
    ]
