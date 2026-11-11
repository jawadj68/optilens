from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .forms import PatientCsvImportForm, PatientForm, PatientVisitForm
from .import_services import import_patients_from_csv
from .models import ClinicalRecord, Patient, PatientVisit
from .patient_search import patient_search_queryset


def _staff_required(user) -> bool:
    return user.is_staff or user.is_superuser


def _patient_list_context(request):
    q = request.GET.get("q", "").strip()
    qs = patient_search_queryset(q)
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))
    return {
        "page": page,
        "q": q,
        "total_patients": Patient.objects.count(),
        "filtered_count": paginator.count,
        "optilens_nav": "patients",
    }


def _visit_list_context(request):
    q = request.GET.get("q", "").strip()
    qs = (
        PatientVisit.objects.select_related("patient")
        .all()
        .order_by("-pk")
    )
    if q:
        qs = qs.filter(
            Q(patient__full_name__icontains=q)
            | Q(treatment__icontains=q)
            | Q(lens_prescription__icontains=q)
            | Q(notes__icontains=q)
        )
        if q.isdigit():
            n = int(q)
            qs = qs.filter(Q(visit_nb=n) | Q(patient__patient_nb=n))
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))
    return {
        "page": page,
        "q": q,
        "total_visits": PatientVisit.objects.count(),
        "filtered_count": paginator.count,
        "optilens_nav": "seances",
    }


@login_required
def patient_list(request):
    context = _patient_list_context(request)
    if request.GET.get("partial"):
        return render(request, "optilens/patient_list_results.html", context)
    return render(request, "optilens/patient_list.html", context)


@login_required
def visit_list(request):
    context = _visit_list_context(request)
    if request.GET.get("partial"):
        return render(request, "optilens/visit_list_results.html", context)
    return render(request, "optilens/visit_list.html", context)


@login_required
@require_GET
def patient_by_nb(request, nb: int):
    patient = get_object_or_404(Patient, patient_nb=nb)
    return redirect("optilens:patient_detail", pk=patient.pk)


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    visits = patient.visits.all()[:100]
    clinical_records = patient.clinical_records.all()[:50]
    return render(
        request,
        "optilens/patient_detail.html",
        {
            "patient": patient,
            "visits": visits,
            "visit_count": patient.visits.count(),
            "clinical_records": clinical_records,
            "clinical_count": patient.clinical_records.count(),
            "optilens_nav": "patients",
        },
    )


@login_required
def clinical_record_detail(request, pk):
    record = get_object_or_404(ClinicalRecord.objects.select_related("patient"), pk=pk)
    nav = "clinical_unmatched" if record.patient_id is None else "patients"
    return render(
        request,
        "optilens/clinical_record_detail.html",
        {"record": record, "optilens_nav": nav},
    )


@login_required
def clinical_unmatched_list(request):
    q = request.GET.get("q", "").strip()
    qs = ClinicalRecord.objects.filter(patient__isnull=True).order_by(
        "-record_date", "-dossier_nr"
    )
    if q:
        qs = qs.filter(
            Q(patient_name_snapshot__icontains=q)
            | Q(summary__icontains=q)
            | Q(data__icontains=q)
        )
        if q.isdigit():
            qs = qs.filter(dossier_nr=int(q))
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "optilens/clinical_unmatched_list.html",
        {
            "page": page,
            "q": q,
            "total_unmatched": ClinicalRecord.objects.filter(patient__isnull=True).count(),
            "filtered_count": paginator.count,
            "optilens_nav": "clinical_unmatched",
        },
    )


@login_required
def patient_create(request):
    if request.method == "POST":
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f"Patient « {patient.full_name} » créé.")
            return redirect("optilens:patient_detail", pk=patient.pk)
    else:
        form = PatientForm()
    return render(
        request,
        "optilens/patient_form.html",
        {"form": form, "title": "Nouveau patient", "optilens_nav": "patients"},
    )


@login_required
def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == "POST":
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            patient = form.save()
            messages.success(request, "Fiche patient enregistrée.")
            return redirect("optilens:patient_detail", pk=patient.pk)
    else:
        form = PatientForm(instance=patient)
    return render(
        request,
        "optilens/patient_form.html",
        {
            "form": form,
            "title": f"Modifier — {patient.full_name}",
            "patient": patient,
            "optilens_nav": "patients",
        },
    )


@login_required
def patient_add_visit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == "POST":
        form = PatientVisitForm(request.POST)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.patient = patient
            visit.save()
            messages.success(request, "Séance ajoutée.")
            return redirect("optilens:patient_detail", pk=patient.pk)
    else:
        form = PatientVisitForm()
    return render(
        request,
        "optilens/visit_form.html",
        {"form": form, "patient": patient, "optilens_nav": "patients"},
    )


@login_required
def import_csv(request):
    if not _staff_required(request.user):
        messages.error(request, "Import réservé au personnel autorisé.")
        return redirect("optilens:patient_list")

    result = None
    if request.method == "POST":
        form = PatientCsvImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data["file"].read()
            dry_run = form.cleaned_data["dry_run"]
            result = import_patients_from_csv(uploaded, dry_run=dry_run)
            if dry_run:
                messages.info(
                    request,
                    f"Simulation : {result['created']} ligne(s) prêtes à importer, "
                    f"{result['skipped']} ignorée(s).",
                )
            else:
                messages.success(
                    request,
                    f"Import terminé : {result['created']} créé(s), "
                    f"{result['updated']} mis à jour, {result['skipped']} ignoré(s).",
                )
                return redirect("optilens:patient_list")
    else:
        form = PatientCsvImportForm(initial={"dry_run": True})

    return render(
        request,
        "optilens/import_csv.html",
        {
            "form": form,
            "result": result,
            "optilens_nav": "import",
        },
    )


@login_required
@require_POST
def patient_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Suppression réservée au superutilisateur.")
        return redirect("optilens:patient_detail", pk=pk)
    patient = get_object_or_404(Patient, pk=pk)
    name = patient.full_name
    patient.delete()
    messages.success(request, f"Patient « {name} » supprimé.")
    return redirect("optilens:patient_list")
