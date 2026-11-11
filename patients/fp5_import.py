from __future__ import annotations

from collections import OrderedDict
from typing import Any

from fp5dump.fp5file.blockchain import decode_vli, split_field_and_sub_ref
from fp5dump.fp5file.fp5file import FP5File

from .models import Patient, PatientVisit

# FileMaker field id (single-byte hex in this file) → handler
TEXT_FIELDS = {
    bytes.fromhex("02"): "full_name",
    bytes.fromhex("06"): "address",
    bytes.fromhex("1a"): "father_name",
    bytes.fromhex("21"): "sex",
    bytes.fromhex("23"): "profession",
    bytes.fromhex("24"): "loisirs",
    bytes.fromhex("2c"): "treatment",
}

REPEATING_TEXT = {
    bytes.fromhex("07"): "phone",
    bytes.fromhex("09"): "antecedents",
}

LENS_NUMBER_LABELS = {
    bytes.fromhex("25"): "OD SPH",
    bytes.fromhex("26"): "OG SPH",
    bytes.fromhex("27"): "OD CYL",
    bytes.fromhex("28"): "OG CYL",
    bytes.fromhex("29"): "OD AXE",
    bytes.fromhex("2a"): "OG AXE",
    bytes.fromhex("2b"): "ADDITION",
}


def _decode_value(raw: bytes | Any, encoding: str) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        return raw.decode(encoding, errors="replace").strip()
    return str(raw).strip()


def _normalize_sex(raw: str) -> str:
    s = (raw or "").strip().upper()
    if s in {"M", "H", "HOMME", "MALE"}:
        return Patient.Sex.MALE
    if s in {"F", "FEMME", "FEMALE"}:
        return Patient.Sex.FEMALE
    return ""


def _parse_int_field(text: str) -> int | None:
    cleaned = (text or "").strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def _parse_record(tokens: dict, encoding: str) -> dict[str, str | int]:
    values: dict[str, list[str]] = {}
    lens_parts: list[str] = []
    patient_nb: int | None = None

    for key, raw in tokens.items():
        field_id, sub = split_field_and_sub_ref(key)
        text = _decode_value(raw, encoding)
        if not text:
            continue

        if field_id == bytes.fromhex("01"):
            patient_nb = _parse_int_field(text)
            continue

        if field_id in TEXT_FIELDS:
            name = TEXT_FIELDS[field_id]
            values.setdefault(name, []).append(text)
        elif field_id in REPEATING_TEXT:
            name = REPEATING_TEXT[field_id]
            values.setdefault(name, []).append(text)
        elif field_id in LENS_NUMBER_LABELS:
            lens_parts.append(f"{LENS_NUMBER_LABELS[field_id]}: {text}")

    def join_field(name: str) -> str:
        return "\n".join(values.get(name, [])).strip()

    full_name = join_field("full_name").replace("\r", "")
    if not full_name:
        return {}

    phone = " / ".join(x for x in values.get("phone", []) if x)
    antecedents = "\n".join(x for x in values.get("antecedents", []) if x)

    out: dict[str, str | int | None] = {
        "patient_nb": patient_nb,
        "full_name": full_name[:200],
        "sex": _normalize_sex(join_field("sex")),
        "address": join_field("address"),
        "phone": phone[:80],
        "father_name": join_field("father_name")[:200],
        "profession": join_field("profession")[:120],
        "loisirs": join_field("loisirs"),
        "antecedents": antecedents,
        "notes": join_field("treatment"),
        "lens_prescription": "\n".join(lens_parts),
    }
    return out


def _record_mod_id(tokens: dict) -> int:
    raw = tokens.get(b"\xfc")
    if not raw:
        return 0
    return int.from_bytes(raw, byteorder="big")


def import_patients_from_fp5(
    path: str,
    *,
    encoding: str = "cp1252",
    dry_run: bool = True,
    dedupe_by_name: bool = True,
) -> dict[str, Any]:
    best_by_name: OrderedDict[str, tuple[int, int, dict[str, str]]] = OrderedDict()
    skipped_empty = 0
    raw_count = 0

    with FP5File(path, encoding=encoding) as fp5:
        for rec_id_bin, tokens in fp5.data.sub_nodes(b"\x05"):
            raw_count += 1
            record_id = decode_vli(rec_id_bin)
            parsed = _parse_record(tokens, fp5.encoding)
            if not parsed:
                skipped_empty += 1
                continue
            mod_id = _record_mod_id(tokens)
            key = parsed["full_name"].strip().lower()
            if dedupe_by_name:
                prev = best_by_name.get(key)
                if prev is None or mod_id >= prev[0]:
                    best_by_name[key] = (mod_id, record_id, parsed)
            else:
                best_by_name[f"{key}#{record_id}"] = (mod_id, record_id, parsed)

    to_import = list(best_by_name.values())
    created = 0
    updated = 0

    if dry_run:
        return {
            "dry_run": True,
            "raw_records": raw_count,
            "skipped_empty": skipped_empty,
            "to_import": len(to_import),
            "created": len(to_import),
            "updated": 0,
        }

    for mod_id, record_id, parsed in to_import:
        legacy_key = f"fp5-{record_id}"
        lens = parsed.pop("lens_prescription", "")
        treatment = parsed.pop("notes", "")
        defaults = {**parsed}
        patient, was_created = Patient.objects.update_or_create(
            legacy_fm_key=legacy_key,
            defaults=defaults,
        )
        if was_created:
            created += 1
        else:
            updated += 1
        if lens or treatment:
            PatientVisit.objects.get_or_create(
                patient=patient,
                legacy_fm_key=legacy_key,
                defaults={
                    "treatment": treatment,
                    "lens_prescription": lens,
                },
            )

    return {
        "dry_run": False,
        "raw_records": raw_count,
        "skipped_empty": skipped_empty,
        "to_import": len(to_import),
        "created": created,
        "updated": updated,
    }
