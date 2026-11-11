from django.urls import path

from . import views

app_name = "optilens"

urlpatterns = [
    path("", views.patient_list, name="patient_list"),
    path("seances/", views.visit_list, name="visit_list"),
    path("patients/nb/<int:nb>/", views.patient_by_nb, name="patient_by_nb"),
    path("patients/new/", views.patient_create, name="patient_create"),
    path("patients/<int:pk>/", views.patient_detail, name="patient_detail"),
    path("patients/<int:pk>/edit/", views.patient_edit, name="patient_edit"),
    path("patients/<int:pk>/visits/new/", views.patient_add_visit, name="patient_add_visit"),
    path("patients/<int:pk>/delete/", views.patient_delete, name="patient_delete"),
    path("clinical/unmatched/", views.clinical_unmatched_list, name="clinical_unmatched_list"),
    path("clinical/<int:pk>/", views.clinical_record_detail, name="clinical_record_detail"),
    path("import/", views.import_csv, name="import_csv"),
]
