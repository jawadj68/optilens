from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fp5dump.fp5file.blockchain import decode_vli, split_field_and_sub_ref
from fp5dump.fp5file.fp5file import FP5File

from .fp5_import import _decode_value, _parse_int_field
from .models import Patient, PatientVisit

LENS_LABELS = (
    "LUODSPH", "LUODCYL", "LUODAXE", "LUODPRIS", "LUODBASE",
    "LUOGSPH", "LUOGCYL", "LUOGAXE", "LUOGPRIS", "LUOGBASE",
    "ADDITION", "LEODSPH", "LEOGSPH",
)

EXTRA_NOTE_LABELS = (
    "REM LUNETTE", "ARMC", "LIBELLE ACHAT", "E.I.P", "ENTRTIEN", "REM LDC", "TYPE VERRE",
)


def _field_by_label(fp5: FP5File) -> dict[str, bytes]:
    return {fld.label.upper(): fid for fid, fld in fp5.fields.items()}


def _parse_decimal(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(",", ".").strip())
    except (InvalidOperation, AttributeError):
        return None


def _parse_visit_date(raw: str):
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def _parse_seance_tokens(tokens: dict, encoding: str, labels: dict[str, bytes]) -> dict[str, Any]:
    by_id = {labels[k]: k for k in labels if labels.get(k)}

    def get_label(field_id: bytes) -> str | None:
        return by_id.get(field_id)

    scalars: dict[str, str] = {}
    lens_lines: list[str] = []

    for key, raw in tokens.items():
        field_id, _sub = split_field_and_sub_ref(key)
        text = _decode_value(raw, encoding)
        if not text:
            continue
        label = get_label(field_id)
        if not label:
            continue
        if label == "NB":
            scalars["visit_nb"] = text
        elif label in LENS_LABELS:
            lens_lines.append(f"{label}: {text}")
        elif label == "DATE":
            scalars["visit_date_raw"] = text
        elif label == "MED TRAIT":
            scalars["treatment"] = text
        elif label == "PRIX":
            scalars["price"] = text
        elif label == "RECU":
            scalars["received"] = text
        elif label in EXTRA_NOTE_LABELS:
            scalars[label] = text

    visit_nb = _parse_int_field(scalars.get("visit_nb", ""))
    visit_date = _parse_visit_date(scalars.get("visit_date_raw", ""))

    extra_notes = []
    if scalars.get("price"):
        extra_notes.append(f"PRIX: {scalars['price']}")
    for label in EXTRA_NOTE_LABELS:
        if scalars.get(label):
            extra_notes.append(f"{label}: {scalars[label]}")

    return {
        "visit_nb": visit_nb,
        "visit_date": visit_date,
        "treatment": scalars.get("treatment", ""),
        "lens_prescription": "\n".join(lens_lines),
        "deposit": _parse_decimal(scalars.get("received", "")),
        "notes": "\n".join(extra_notes),
    }


def _resolve_patient(visit_nb: int) -> Patient | None:
    patient = Patient.objects.filter(patient_nb=visit_nb).first()
    if patient:
        return patient
    visit = (
        PatientVisit.objects.filter(visit_nb=visit_nb)
        .select_related("patient")
        .order_by("-pk")
        .first()
    )
    if visit:
        return visit.patient
    return None


def import_visits_from_seance_fp5(
    path: str,
    *,
    encoding: str = "cp1252",
    dry_run: bool = True,
    enrich_existing: bool = True,
) -> dict[str, Any]:
    created = 0
    updated = 0
    enriched = 0
    skipped = 0
    scanned = 0
    field_names: list[str] = []

    with FP5File(path, encoding=encoding) as fp5:
        field_names = sorted({fld.label for fld in fp5.fields.values()})
        labels = _field_by_label(fp5)

        for rec_id_bin, tokens in fp5.data.sub_nodes(b"\x05"):
            scanned += 1
            record_id = decode_vli(rec_id_bin)
            row = _parse_seance_tokens(tokens, fp5.encoding, labels)
            visit_nb = row.get("visit_nb")
            if visit_nb is None:
                skipped += 1
                continue

            patient = _resolve_patient(visit_nb)
            if patient is None:
                skipped += 1
                continue

            legacy_key = f"seance~1-{record_id}"

            if dry_run:
                created += 1
                continue

            defaults = {
                "patient": patient,
                "visit_nb": visit_nb,
                "visit_date": row.get("visit_date"),
                "treatment": row.get("treatment", ""),
                "lens_prescription": row.get("lens_prescription", ""),
                "deposit": row.get("deposit"),
                "notes": row.get("notes", ""),
            }

            existing = PatientVisit.objects.filter(legacy_fm_key=legacy_key).first()
            if existing:
                for attr, val in defaults.items():
                    setattr(existing, attr, val)
                existing.save()
                updated += 1
                continue

            if enrich_existing:
                stub = (
                    PatientVisit.objects.filter(visit_nb=visit_nb, legacy_fm_key__startswith="fp5-")
                    .order_by("-pk")
                    .first()
                )
                if stub and not PatientVisit.objects.filter(legacy_fm_key=legacy_key).exists():
                    for attr, val in defaults.items():
                        setattr(stub, attr, val)
                    stub.legacy_fm_key = legacy_key
                    stub.save()
                    enriched += 1
                    continue

            PatientVisit.objects.create(legacy_fm_key=legacy_key, **defaults)
            created += 1

    return {
        "dry_run": dry_run,
        "scanned": scanned,
        "created": created,
        "updated": updated,
        "enriched": enriched,
        "skipped": skipped,
        "field_names": field_names,
    }
