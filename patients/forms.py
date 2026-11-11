from django import forms

from .models import Patient, PatientVisit


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "patient_nb",
            "full_name",
            "sex",
            "phone",
            "address",
            "profession",
            "father_name",
            "region",
            "antecedents",
            "risk_factors",
            "loisirs",
            "notes",
            "archive_notes",
            "is_active",
        ]
        widgets = {
            "patient_nb": forms.NumberInput(attrs={"class": "form-control"}),
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "sex": forms.Select(attrs={"class": "form-select"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "profession": forms.TextInput(attrs={"class": "form-control"}),
            "father_name": forms.TextInput(attrs={"class": "form-control"}),
            "region": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "address": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "antecedents": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "risk_factors": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "loisirs": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "archive_notes": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class PatientVisitForm(forms.ModelForm):
    class Meta:
        model = PatientVisit
        fields = ["visit_date", "treatment", "lens_prescription", "deposit", "notes"]
        widgets = {
            "visit_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "treatment": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "lens_prescription": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "deposit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class PatientCsvImportForm(forms.Form):
    file = forms.FileField(
        label="Fichier CSV (export FileMaker)",
        help_text="Export Tab/CSV depuis FileMaker 5 — encodage UTF-8 ou Windows-1252.",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )
    dry_run = forms.BooleanField(
        required=False,
        initial=True,
        label="Simulation (ne pas enregistrer)",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
