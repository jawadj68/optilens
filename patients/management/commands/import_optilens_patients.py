from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from patients.import_services import import_patients_from_csv


class Command(BaseCommand):
    help = "Import patients from a FileMaker CSV export."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to the exported CSV file")
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Write to database (default is dry-run simulation)",
        )

    def handle(self, *args, **options):
        path = Path(options["csv_path"])
        if not path.is_file():
            raise CommandError(f"File not found: {path}")
        data = path.read_bytes()
        dry_run = not options["commit"]
        result = import_patients_from_csv(data, dry_run=dry_run)
        self.stdout.write(f"Headers: {', '.join(result.get('headers', []))[:500]}")
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN — would create {result['created']}, "
                    f"skip {result['skipped']}. Use --commit to save."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created {result['created']}, updated {result['updated']}, "
                    f"skipped {result['skipped']}."
                )
            )
        for err in result.get("errors") or []:
            self.stdout.write(self.style.NOTICE(err))
