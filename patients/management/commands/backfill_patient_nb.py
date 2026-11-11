from collections import OrderedDict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from fp5dump.fp5file.blockchain import decode_vli
from fp5dump.fp5file.fp5file import FP5File

from patients.fp5_import import _parse_record, _record_mod_id
from patients.models import Patient

DEFAULT_FP5 = Path(r"C:\Users\RMJ\Desktop\FileMaker Pro 5\System\PATIEN~1 Copy.FP5")


class Command(BaseCommand):
    help = "Backfill patient_nb (FileMaker Nb) on existing patients from .fp5."

    def add_arguments(self, parser):
        parser.add_argument("fp5_path", nargs="?", default=str(DEFAULT_FP5))

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["fp5_path"])
        if not path.is_file():
            raise CommandError(f"File not found: {path}")

        winners: OrderedDict[str, tuple[int, int, int]] = OrderedDict()
        with FP5File(str(path), encoding="cp1252") as fp5:
            for rec_id_bin, tokens in fp5.data.sub_nodes(b"\x05"):
                parsed = _parse_record(tokens, fp5.encoding)
                nb = parsed.get("patient_nb") if parsed else None
                if not parsed or nb is None:
                    continue
                record_id = decode_vli(rec_id_bin)
                mod_id = _record_mod_id(tokens)
                key = str(parsed["full_name"]).strip().lower()
                prev = winners.get(key)
                if prev is None or mod_id >= prev[0]:
                    winners[key] = (mod_id, record_id, int(nb))

        updated = 0
        missing = 0
        for _mod, record_id, nb in winners.values():
            legacy = f"fp5-{record_id}"
            changed = Patient.objects.filter(legacy_fm_key=legacy).update(patient_nb=nb)
            if changed:
                updated += changed
            else:
                missing += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"patient_nb set on {updated} row(s); {missing} legacy keys not found in DB."
            )
        )
