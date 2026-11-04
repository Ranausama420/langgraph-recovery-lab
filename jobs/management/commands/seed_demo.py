from django.core.management.base import BaseCommand

from jobs.models import Job
from jobs.worker import run_job


class Command(BaseCommand):
    help = "Create the deterministic PulseOps demo jobs for a tenant."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", default="acme")

    def handle(self, *args, **options):
        tenant = options["tenant"]
        seeds = [
            ("Generate monthly usage summary", "report", "seed-summary-001", 3),
            ("Notify customer about maintenance", "unstable_email", "seed-email-001", 3),
            ("Validate customer export", "validation", "seed-validation-001", 2),
        ]
        for task, tool, key, max_attempts in seeds:
            job, created = Job.objects.get_or_create(
                tenant_id=tenant,
                idempotency_key=key,
                defaults={"task": task, "tool": tool, "max_attempts": max_attempts},
            )
            if created:
                run_job(job)
                if job.status == "retrying":
                    run_job(job)
                self.stdout.write(self.style.SUCCESS(f"Created {tool}: {job.status}"))
            else:
                self.stdout.write(f"Skipped existing {key}")
