import re
import unicodedata

from .models import Patient


def normalize_person_name(value: str) -> str:
    text = (value or "").strip().upper()
    # Legacy FP5 / mixed encodings (e.g. FRAN‚OIS for François)
    text = text.replace("‚", "C").replace("ƒ", "F")
    text = re.sub(r"\bFRAN\s+OIS\b", "FRANCOIS", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _name_tokens(value: str) -> set[str]:
    return {t for t in normalize_person_name(value).split() if len(t) > 1}


class PatientNameIndex:
    """In-memory index for linking legacy FileMaker names to patients."""

    def __init__(self) -> None:
        self._by_norm: dict[str, list[Patient]] = {}
        self._token_rows: list[tuple[Patient, set[str]]] = []
        self._by_nb: dict[int, Patient] = {}
        for patient in Patient.objects.only("id", "full_name", "patient_nb"):
            norm = normalize_person_name(patient.full_name)
            if norm:
                self._by_norm.setdefault(norm, []).append(patient)
            tokens = _name_tokens(patient.full_name)
            if tokens:
                self._token_rows.append((patient, tokens))
            if patient.patient_nb is not None:
                self._by_nb[patient.patient_nb] = patient

    def by_nb(self, nb: int) -> Patient | None:
        return self._by_nb.get(nb)

    def by_name(self, nom: str) -> Patient | None:
        nom_norm = normalize_person_name(nom)
        if not nom_norm:
            return None

        exact = self._by_norm.get(nom_norm)
        if exact:
            return exact[0]

        tokens = _name_tokens(nom)
        if len(tokens) < 2:
            return Patient.objects.filter(full_name__icontains=nom.strip()).first()

        best: Patient | None = None
        best_score = 0
        for patient, pt in self._token_rows:
            score = len(tokens & pt)
            if score > best_score and score >= min(2, len(tokens)):
                best_score = score
                best = patient
        return best


def find_patient_by_name(nom: str) -> Patient | None:
    return PatientNameIndex().by_name(nom)
