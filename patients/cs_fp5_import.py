from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from fp5dump.fp5file.blockchain import decode_vli, split_field_and_sub_ref
from fp5dump.fp5file.fp5file import FP5File

from .fp5_import import _decode_value, _parse_int_field
from .models import ClinicalRecord
from .patient_match import PatientNameIndex, normalize_person_name

SUMMARY_KEYS = (
    "COMPLAINTES:",
    "OBSERVATIONS:",
    "REMARQUES:",
    "ANTECEDANTS:",
    "DATE:",
    "DATE DE NAISSANCE:",
    "PROFESSION:",
    "TRAITEMENT A.R/M.C:",
    "CONTROLES:",
)


def _parse_record_date(raw: str):
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def _parse_cs_record(tokens: dict, fp5: FP5File) -> dict[str, Any]:
    data: dict[str, str] = {}
    dossier_nr: int | None = None
    nom = ""
    record_date = None

    for key, raw in tokens.items():
        field_id, _sub = split_field_and_sub_ref(key)
        field = fp5.fields.get(field_id)
        if not field or not field.stored:
            continue
        text = _decode_value(raw, fp5.encoding)
        if not text:
            continue
        label = field.label
        data[label] = text
        if label == "Nr.DOSSIER":
            dossier_nr = _parse_int_field(text)
        elif label.startswith("NOM"):
            nom = text
        elif label == "DATE:" and record_date is None:
            record_date = _parse_record_date(text)
        elif label.startswith("DATE") and record_date is None:
            record_date = _parse_record_date(text)

    summary_parts = []
    for k in SUMMARY_KEYS:
        if data.get(k):
            summary_parts.append(f"{k} {data[k]}")

    return {
        "dossier_nr": dossier_nr,
        "nom": nom,
        "record_date": record_date,
        "data": data,
        "summary": "\n".join(summary_parts)[:8000],
    }


def import_clinical_records_from_fp5(
    path: str,
    *,
    source: str,
    encoding: str = "cp1252",
    dry_run: bool = True,
    import_unmatched: bool = True,
) -> dict[str, Any]:
    if source not in ClinicalRecord.Source.values:
        raise ValueError(f"Unknown source {source}")

    created = 0
    updated = 0
    orphans = 0
    orphans_updated = 0
    skipped = 0
    scanned = 0
    unmatched_names: list[str] = []
    name_index = PatientNameIndex()

    with FP5File(path, encoding=encoding) as fp5:
        for rec_id_bin, tokens in fp5.data.sub_nodes(b"\x05"):
            scanned += 1
            record_id = decode_vli(rec_id_bin)
            row = _parse_cs_record(tokens, fp5)
            dossier_nr = row.get("dossier_nr")
            nom = row.get("nom", "")
            if dossier_nr is None and not nom:
                skipped += 1
                continue

            patient = name_index.by_name(nom) if nom else None
            if patient is None and dossier_nr is not None:
                patient = name_index.by_nb(dossier_nr)

            if patient is None and not import_unmatched:
                skipped += 1
                if nom and len(unmatched_names) < 15:
                    unmatched_names.append(nom)
                continue

            legacy_key = f"{source}-fp5-{record_id}"
            name_snap = ((nom or "").strip() or normalize_person_name(nom))[:220]

            if dry_run:
                if patient:
                    created += 1
                else:
                    orphans += 1
                continue

            defaults = {
                "patient": patient,
                "dossier_nr": dossier_nr or 0,
                "source": source,
                "record_date": row.get("record_date"),
                "patient_name_snapshot": name_snap,
                "summary": row.get("summary", ""),
                "data": row.get("data", {}),
            }

            _obj, was_created = ClinicalRecord.objects.update_or_create(
                legacy_fm_key=legacy_key,
                defaults=defaults,
            )
            if patient is None:
                if was_created:
                    orphans += 1
                else:
                    orphans_updated += 1
            elif was_created:
                created += 1
            else:
                updated += 1

    return {
        "dry_run": dry_run,
        "scanned": scanned,
        "created": created,
        "updated": updated,
        "orphans": orphans,
        "orphans_updated": orphans_updated,
        "skipped": skipped,
        "unmatched_sample": unmatched_names,
    }
