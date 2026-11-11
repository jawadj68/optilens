from django.db import migrations, models


def mark_existing_links_auto(apps, schema_editor):
    ClinicalRecord = apps.get_model("patients", "ClinicalRecord")
    ClinicalRecord.objects.filter(patient__isnull=False).update(link_method="auto")


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0005_clinicalrecord_null_patient'),
    ]

    operations = [
        migrations.AddField(
            model_name='clinicalrecord',
            name='link_method',
            field=models.CharField(blank=True, choices=[('auto', 'Automatique (nom identique)'), ('manual', 'Lié manuellement'), ('created', 'Patient créé depuis la fiche')], help_text='Les liens manuels ne sont jamais modifiés par un nouvel import', max_length=10, verbose_name='Type de lien'),
        ),
        migrations.RunPython(mark_existing_links_auto, migrations.RunPython.noop),
    ]
