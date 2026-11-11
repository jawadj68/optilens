import difflib
import re
import unicodedata
from dataclasses import dataclass

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


TITLE_WORDS = frozenset({"DR", "MR", "MME", "MLLE", "MRS", "MISS", "SOEUR", "SR", "MAMAN", "PAPA"})


def _name_tokens(value: str) -> frozenset[str]:
    return frozenset(
        t for t in normalize_person_name(value).split() if len(t) > 1 and t not in TITLE_WORDS
    )


def _sorted_name(tokens: frozenset[str]) -> str:
    return " ".join(sorted(tokens))


def phone_keys(value: str) -> set[str]:
    """Last 6 digits of each phone number in a free-text field (03/210203, 06-570742 / 71...)."""
    keys = set()
    for number in re.findall(r"\d+(?:[/\-.]\d+)*", value or ""):
        digits = re.sub(r"\D", "", number)
        if len(digits) >= 6:
            keys.add(digits[-6:])
    return keys


@dataclass
class PatientSuggestion:
    patient: Patient
    score: float
    same_phone: bool

    @property
    def percent(self) -> int:
        return round(min(self.score, 1.0) * 100)


class PatientNameIndex:
    """In-memory index for linking legacy FileMaker names to patients."""

    def __init__(self) -> None:
        self._by_tokens: dict[frozenset[str], list[Patient]] = {}
        self._by_token: dict[str, list[tuple[Patient, frozenset[str]]]] = {}
        self._by_nb: dict[int, Patient] = {}
        self._by_phone: dict[str, list[Patient]] = {}
        for patient in Patient.objects.only("id", "full_name", "patient_nb", "phone"):
            tokens = _name_tokens(patient.full_name)
            if tokens:
                self._by_tokens.setdefault(tokens, []).append(patient)
                for t in tokens:
                    self._by_token.setdefault(t, []).append((patient, tokens))
            if patient.patient_nb is not None:
                self._by_nb[patient.patient_nb] = patient
            for key in phone_keys(patient.phone):
                self._by_phone.setdefault(key, []).append(patient)
        self._token_list = list(self._by_token)

    def by_nb(self, nb: int) -> Patient | None:
        return self._by_nb.get(nb)

    def by_name(self, nom: str) -> Patient | None:
        """Only unambiguous cases; family names are widely shared, so anything else goes to review.

        1. Same name words in any order, and only one such patient.
        2. Otherwise, one name contains the other, the patient has the record's surname and
           first name, and only one patient fits that way. CS names are written
           "SURNAME FIRST FATHER", so a patient matching only surname + father is the father.
        """
        tokens = _name_tokens(nom)
        if len(tokens) < 2:
            return None
        exact = self._by_tokens.get(tokens, [])
        if exact:
            return exact[0] if len(exact) == 1 else None

        surname_and_first = _name_tokens(" ".join((nom or "").split()[:2]))
        nested: dict[int, Patient] = {}
        for t in tokens:
            for patient, pt in self._by_token.get(t, []):
                if surname_and_first <= pt and (pt < tokens or tokens < pt):
                    nested[patient.pk] = patient
        return next(iter(nested.values())) if len(nested) == 1 else None

    def suggest(self, nom: str, phone: str = "", limit: int = 6) -> list[PatientSuggestion]:
        tokens = _name_tokens(nom)
        phones = phone_keys(phone)
        candidates: dict[int, tuple[Patient, frozenset[str]]] = {}
        for t in tokens:
            for close in difflib.get_close_matches(t, self._token_list, n=4, cutoff=0.8):
                for patient, pt in self._by_token[close]:
                    candidates[patient.pk] = (patient, pt)
        phone_hits = {p.pk for key in phones for p in self._by_phone.get(key, [])}
        for key in phones:
            for patient in self._by_phone.get(key, []):
                candidates.setdefault(patient.pk, (patient, _name_tokens(patient.full_name)))

        query = _sorted_name(tokens)
        results = []
        for patient, pt in candidates.values():
            score = difflib.SequenceMatcher(None, query, _sorted_name(pt)).ratio()
            same_phone = patient.pk in phone_hits
            if same_phone:
                score += 0.3
            if score >= 0.6:
                results.append(PatientSuggestion(patient, score, same_phone))
        results.sort(key=lambda s: s.score, reverse=True)
        return results[:limit]


_cached_index: tuple[tuple, PatientNameIndex] | None = None


def get_name_index() -> PatientNameIndex:
    """Shared index for web views, rebuilt when patients are added or edited."""
    global _cached_index
    from django.db.models import Count, Max

    stamp = tuple(Patient.objects.aggregate(n=Count("id"), last=Max("updated_at")).values())
    if _cached_index is None or _cached_index[0] != stamp:
        _cached_index = (stamp, PatientNameIndex())
    return _cached_index[1]


def find_patient_by_name(nom: str) -> Patient | None:
    return PatientNameIndex().by_name(nom)
