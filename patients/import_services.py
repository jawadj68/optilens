import csv
import io
import re
from typing import Any

from .models import Patient

HEADER_ALIASES: dict[str, str] = {
    "NAME": "full_name",
    "NOM": "full_name",
    "PATIENT": "full_name",
    "PATIENTS": "full_name",
    "IDENTITE": "full_name",
    "SEXE": "sex",
    "SEXEB": "sex",
    "TELEPHONNE": "phone",
    "TELEPHONNEB": "phone",
    "ADRESSE": "address",
    "ADRESSEB": "address",
    "PROFESSION": "profession",
    "NOM PERE": "father_name",
    "NOM PEREB": "father_name",
    "NOM PERED": "father_name",
    "ANTECEDANTS": "antecedents",
    "ANTECEDANTSB": "antecedents",
    "FACTEURS DE RISQUE": "risk_factors",
    "FACTEURS DE RISQUEB": "risk_factors",
    "LOISIRS": "loisirs",
    "ADDITION": "notes",
    "TRAITEMENT": "notes",
    "TRAITEMENTB": "archive_notes",
    "ZGHARTA": "region",
    "HASROUN": "region",
    "MIZIARA": "region",
    "TRIPOLI": "region",
    "BECHARRE": "region",
}


def _normalize_header(label: str) -> str:
    return re.sub(r"\s+", " ", (label or "").strip().upper())


def _map_row(headers: list[str], row: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for header, value in zip(headers, row):
        key = HEADER_ALIASES.get(_normalize_header(header))
        if not key:
            continue
        text = (value or "").strip()
        if not text:
            continue
        if key in out:
            out[key] = f"{out[key]}\n{text}"
        else:
            out[key] = text
    return out


def _normalize_sex(raw: str) -> str:
    s = (raw or "").strip().upper()
    if s in {"M", "H", "HOMME", "MALE"}:
        return Patient.Sex.MALE
    if s in {"F", "FEMME", "FEMALE"}:
        return Patient.Sex.FEMALE
    return ""


def decode_csv_bytes(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def sniff_dialect(text: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        return csv.excel_tab


def import_patients_from_csv(
    data: bytes,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    text = decode_csv_bytes(data)
    reader = csv.reader(io.StringIO(text), dialect=sniff_dialect(text))
    try:
        headers = [h.strip() for h in next(reader)]
    except StopIteration:
        return {"created": 0, "updated": 0, "skipped": 0, "errors": ["Fichier vide."]}

    created = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    for line_no, row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in row):
            skipped += 1
            continue
        mapped = _map_row(headers, row)
        name = mapped.get("full_name", "").strip()
        if not name:
            skipped += 1
            errors.append(f"Ligne {line_no}: nom patient manquant, ignorée.")
            continue

        defaults = {
            "sex": _normalize_sex(mapped.get("sex", "")),
            "phone": mapped.get("phone", "")[:80],
            "address": mapped.get("address", ""),
            "profession": mapped.get("profession", "")[:120],
            "father_name": mapped.get("father_name", "")[:200],
            "region": mapped.get("region", "")[:80],
            "antecedents": mapped.get("antecedents", ""),
            "risk_factors": mapped.get("risk_factors", ""),
            "loisirs": mapped.get("loisirs", ""),
            "notes": mapped.get("notes", ""),
            "archive_notes": mapped.get("archive_notes", ""),
        }
        legacy_key = f"csv-line-{line_no}"

        if dry_run:
            created += 1
            continue

        _obj, was_created = Patient.objects.update_or_create(
            legacy_fm_key=legacy_key,
            defaults={"full_name": name[:200], **defaults},
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:20],
        "headers": headers,
        "dry_run": dry_run,
    }
