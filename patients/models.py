from django.db import models


class Patient(models.Model):
    class Sex(models.TextChoices):
        MALE = "M", "Homme"
        FEMALE = "F", "Femme"
        OTHER = "O", "Autre"

    patient_nb = models.IntegerField(
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        verbose_name="Nb",
        help_text="Numéro patient FileMaker (lien avec les autres tables)",
    )
    full_name = models.CharField(max_length=200)
    sex = models.CharField(max_length=1, choices=Sex.choices, blank=True)
    phone = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    profession = models.CharField(max_length=120, blank=True)
    father_name = models.CharField(max_length=200, blank=True, verbose_name="Nom du père")
    region = models.CharField(max_length=80, blank=True, help_text="Village / secteur (ex. Zgharta, Hasroun)")
    antecedents = models.TextField(blank=True)
    risk_factors = models.TextField(blank=True, verbose_name="Facteurs de risque")
    loisirs = models.TextField(blank=True)
    notes = models.TextField(blank=True, verbose_name="Remarques / addition")
    archive_notes = models.TextField(
        blank=True,
        help_text="Champs « B » ou données historiques importées de FileMaker",
    )
    legacy_fm_key = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="Identifiant d’import FileMaker (si disponible)",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name", "pk"]
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self) -> str:
        return self.full_name


class PatientVisit(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="visits")
    visit_nb = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Nb (ligne FileMaker)",
        help_text="Numéro Nb de la ligne d’origine (peut différer du Nb patient)",
    )
    visit_date = models.DateField(null=True, blank=True, verbose_name="Date de séance")
    treatment = models.TextField(blank=True, verbose_name="Traitement")
    lens_prescription = models.TextField(blank=True, verbose_name="Lentilles / prescription")
    deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Acompte",
    )
    notes = models.TextField(blank=True)
    legacy_fm_key = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-visit_date", "-pk"]
        verbose_name = "Séance"
        verbose_name_plural = "Séances"

    def __str__(self) -> str:
        when = self.visit_date.isoformat() if self.visit_date else "sans date"
        return f"{self.patient.full_name} — {when}"


class ClinicalRecord(models.Model):
    class Source(models.TextChoices):
        CS = "cs", "CS (fiche clinique)"
        CSOLD = "csold", "CS ancien"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="clinical_records",
        null=True,
        blank=True,
        help_text="Vide si aucun patient Optilens ne correspond au nom CS",
    )
    dossier_nr = models.IntegerField(db_index=True, verbose_name="Nr. dossier")
    source = models.CharField(max_length=10, choices=Source.choices)
    record_date = models.DateField(null=True, blank=True, verbose_name="Date fiche")
    patient_name_snapshot = models.CharField(max_length=220, blank=True)
    summary = models.TextField(
        blank=True,
        help_text="Résumé lisible (plaintes, observations, remarques)",
    )
    data = models.JSONField(default=dict, blank=True)
    legacy_fm_key = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-record_date", "-dossier_nr"]
        verbose_name = "Fiche clinique"
        verbose_name_plural = "Fiches cliniques"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "dossier_nr"],
                name="uniq_clinical_dossier_per_source",
            ),
        ]

    def __str__(self) -> str:
        if self.patient_id:
            return f"Dossier {self.dossier_nr} — {self.patient.full_name}"
        label = self.patient_name_snapshot or "patient inconnu"
        return f"Dossier {self.dossier_nr} — {label} (non lié)"
