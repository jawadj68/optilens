from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from patients.cs_fp5_import import import_clinical_records_from_fp5

BASE = Path(r"C:\Users\RMJ\Desktop\FileMaker Pro 5\System")


class Command(BaseCommand):
    help = "Import CS / CSOLD clinical forms and link to patients by name (Nr.DOSSIER)."

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true")
        parser.add_argument(
            "--skip-unmatched",
            action="store_true",
            help="Ne pas enregistrer les fiches sans patient correspondant",
        )
        parser.add_argument("--cs", default=str(BASE / "CS.FP5"))
        parser.add_argument("--csold", default=str(BASE / "CSOLD~1.FP5"))

    def handle(self, *args, **options):
        dry_run = not options["commit"]
        for path, source in ((options["cs"], "cs"), (options["csold"], "csold")):
            p = Path(path)
            if not p.is_file():
                self.stdout.write(self.style.WARNING(f"Skip missing file: {p}"))
                continue
            res = import_clinical_records_from_fp5(
                str(p),
                source=source,
                dry_run=dry_run,
                import_unmatched=not options["skip_unmatched"],
            )
            self.stdout.write(
                f"{p.name}: scanned {res['scanned']}, "
                f"{'would link' if dry_run else 'linked'} {res['created']}, "
                f"updated {res['updated']}, "
                f"{'would orphan' if dry_run else 'orphan'} {res['orphans']}, "
                f"orphan updated {res['orphans_updated']}, skipped {res['skipped']}"
            )
            if res.get("unmatched_sample"):
                self.stdout.write(
                    "Unmatched name sample: " + ", ".join(res["unmatched_sample"][:8])
                )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — add --commit to save."))
