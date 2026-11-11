from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from patients.fp5_import import import_patients_from_fp5

DEFAULT_FP5 = Path(r"C:\Users\RMJ\Desktop\FileMaker Pro 5\System\PATIEN~1 Copy.FP5")


class Command(BaseCommand):
    help = "Import patients directly from a FileMaker .fp5 file (Desktop folder)."

    def add_arguments(self, parser):
        parser.add_argument(
            "fp5_path",
            nargs="?",
            type=str,
            default=str(DEFAULT_FP5),
            help=f"Path to .fp5 file (default: {DEFAULT_FP5})",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Write to database (default is dry-run)",
        )
        parser.add_argument(
            "--encoding",
            default="cp1252",
            help="Text encoding for strings in the file (default: cp1252)",
        )
        parser.add_argument(
            "--keep-all-records",
            action="store_true",
            help="Do not deduplicate by patient name (imports every FileMaker record)",
        )

    def handle(self, *args, **options):
        path = Path(options["fp5_path"])
        if not path.is_file():
            raise CommandError(f"File not found: {path}")

        result = import_patients_from_fp5(
            str(path),
            encoding=options["encoding"],
            dry_run=not options["commit"],
            dedupe_by_name=not options["keep_all_records"],
        )
        self.stdout.write(
            f"File: {path}\n"
            f"Raw record nodes: {result['raw_records']}\n"
            f"Skipped (no name): {result['skipped_empty']}\n"
            f"Patients to import: {result['to_import']}"
        )
        if result["dry_run"]:
            self.stdout.write(
                self.style.WARNING("DRY RUN — use --commit to save to Optilens.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done — created {result['created']}, updated {result['updated']}."
                )
            )
