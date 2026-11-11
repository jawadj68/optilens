from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from patients.fp5_visit_import import import_visits_from_patient_fp5
from patients.seance_fp5_import import import_visits_from_seance_fp5

PATIENTS_FP5 = Path(r"C:\Users\RMJ\Desktop\FileMaker Pro 5\System\PATIEN~1 Copy.FP5")
SEANCE_CANDIDATES = [
    Path(r"C:\Users\RMJ\Desktop\FileMaker Pro 5\System\SEANCE~1.FP5"),
    Path(r"C:\Users\RMJ\Desktop\FileMaker Pro 5\System\SEANCE.fp5"),
    Path(r"C:\Users\RMJ\Desktop\FileMaker Pro 5\System\SEANCE.FP5"),
    Path(r"C:\Users\RMJ\Desktop\SEANCE.fp5"),
]


class Command(BaseCommand):
    help = "Import séances from PATIENTS.fp5 rows and/or SEANCE.fp5 if present."

    def add_arguments(self, parser):
        parser.add_argument(
            "--patients-fp5",
            dest="patients_fp5",
            default=str(PATIENTS_FP5),
            help="Patient database (each FM row → séance)",
        )
        parser.add_argument(
            "--seance-fp5",
            dest="seance_fp5",
            default="",
            help="Optional SEANCE.fp5 path (linked by patient Nb)",
        )
        parser.add_argument("--commit", action="store_true")
        parser.add_argument("--seance-only", action="store_true")
        parser.add_argument("--patients-only", action="store_true")

    def handle(self, *args, **options):
        dry_run = not options["commit"]
        seance_path = options["seance_fp5"].strip()

        if not seance_path:
            for candidate in SEANCE_CANDIDATES:
                if candidate.is_file():
                    seance_path = str(candidate)
                    break

        if not options["seance_only"]:
            ppath = Path(options["patients_fp5"])
            if not ppath.is_file():
                raise CommandError(f"Patients file not found: {ppath}")
            res = import_visits_from_patient_fp5(str(ppath), dry_run=dry_run)
            self.stdout.write(
                f"PATIENTS.fp5: scanned {res['scanned']}, "
                f"visits {'would create' if dry_run else 'created'} {res['created']}, "
                f"updated {res.get('updated', 0)}, "
                f"no patient match {res['skipped_no_patient']}"
            )

        if not options["patients_only"]:
            if not seance_path:
                self.stdout.write(
                    self.style.WARNING(
                        "SEANCE.fp5 not found locally. Copy it from the old PC "
                        "(e.g. C:\\OPTILENS\\SEANCE.FP5 or share \\\\192.168.1.69\\OPTILENS) "
                        "to Desktop\\SEANCE.fp5 and run again."
                    )
                )
                return
            spath = Path(seance_path)
            if not spath.is_file():
                raise CommandError(f"Seance file not found: {spath}")
            res = import_visits_from_seance_fp5(str(spath), dry_run=dry_run)
            self.stdout.write(f"SEANCE.fp5 fields: {', '.join(res.get('field_names', []))}")
            self.stdout.write(
                f"SEANCE.fp5: scanned {res['scanned']}, "
                f"{'would create' if dry_run else 'created'} {res['created']}, "
                f"updated {res.get('updated', 0)}, enriched {res.get('enriched', 0)}, "
                f"skipped {res['skipped']}"
            )
