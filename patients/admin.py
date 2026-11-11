from django.contrib import admin

from .models import ClinicalRecord, Patient, PatientVisit


class PatientVisitInline(admin.TabularInline):
    model = PatientVisit
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("patient_nb", "full_name", "phone", "region", "sex", "is_active", "updated_at")
    list_filter = ("is_active", "sex", "region")
    search_fields = ("full_name", "phone", "legacy_fm_key")
    inlines = [PatientVisitInline]


@admin.register(ClinicalRecord)
class ClinicalRecordAdmin(admin.ModelAdmin):
    list_display = ("dossier_nr", "patient", "patient_name_snapshot", "source", "record_date")
    list_filter = ("source", "patient")
    search_fields = ("patient__full_name", "patient_name_snapshot", "dossier_nr")


@admin.register(PatientVisit)
class PatientVisitAdmin(admin.ModelAdmin):
    list_display = ("patient", "visit_date", "deposit", "created_at")
    list_filter = ("visit_date",)
    search_fields = ("patient__full_name", "notes", "treatment")
