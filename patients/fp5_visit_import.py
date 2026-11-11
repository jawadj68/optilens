from __future__ import annotations

from typing import Any

from fp5dump.fp5file.blockchain import decode_vli
from fp5dump.fp5file.fp5file import FP5File

from .fp5_import import _parse_record
from .models import Patient, PatientVisit


def _patients_by_normalized_name() -> dict[str, Patient]:
    out: dict[str, Patient] = {}
    for p in Patient.objects.all().only("id", "full_name", "patient_nb"):
        key = p.full_name.strip().lower()
        if key and key not in out:
            out[key] = p
    return out


def import_visits_from_patient_fp5(
    path: str,
    *,
    encoding: str = "cp1252",
    dry_run: bool = True,
) -> dict[str, Any]:
    """
    Each FileMaker record row in the patients file becomes a visit (séance),
  linked to the patient with the same name (deduped master row).
    """
    patients = _patients_by_normalized_name()
    created = 0
    skipped_no_patient = 0
    skipped_empty = 0
    updated = 0
    scanned = 0

    with FP5File(path, encoding=encoding) as fp5:
        for rec_id_bin, tokens in fp5.data.sub_nodes(b"\x05"):
            scanned += 1
            record_id = decode_vli(rec_id_bin)
            parsed = _parse_record(tokens, fp5.encoding)
            if not parsed:
                skipped_empty += 1
                continue
            name = str(parsed.get("full_name", "")).strip()
            if not name:
                skipped_empty += 1
                continue
            patient = patients.get(name.lower())
            if patient is None:
                skipped_no_patient += 1
                continue

            visit_nb = parsed.get("patient_nb")
            lens = str(parsed.get("lens_prescription", "") or "")
            treatment = str(parsed.get("notes", "") or "")
            legacy_key = f"fp5-{record_id}"

            if dry_run:
                created += 1
                continue

            visit, was_created = PatientVisit.objects.update_or_create(
                legacy_fm_key=legacy_key,
                defaults={
                    "patient": patient,
                    "visit_nb": visit_nb,
                    "treatment": treatment,
                    "lens_prescription": lens,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

    return {
        "dry_run": dry_run,
        "scanned": scanned,
        "created": created,
        "updated": updated,
        "skipped_no_patient": skipped_no_patient,
        "skipped_empty": skipped_empty,
    }
