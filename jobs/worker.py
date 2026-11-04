from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from .models import Attempt, Job, WorkflowEvent
def run_job(job):
    with transaction.atomic():
        job.current_attempt += 1
        job.status = "running"
        job.next_retry_at = None
        job.save(update_fields=["current_attempt", "status", "next_retry_at", "updated_at"])
        attempt = Attempt.objects.create(job=job, number=job.current_attempt, status="running")
        WorkflowEvent.objects.create(job=job, event="attempt_started", payload={"attempt": attempt.number})
        try:
            if job.tool == "validation":
                raise RuntimeError("Permanent validation failure")
            if job.tool == "unstable_email" and job.current_attempt == 1:
                raise RuntimeError("Temporary email provider timeout")
            job.status = "completed"
            job.result = {"message": f"{job.tool} completed", "attempt": job.current_attempt}
            job.error = ""
            attempt.status = "completed"
        except Exception as error:  # keep unexpected worker failures observable
            job.error = str(error)
            attempt.status = "failed"
            attempt.error = str(error)
            if job.current_attempt < job.max_attempts:
                job.status = "retrying"
                job.next_retry_at = timezone.now() + timedelta(seconds=2 ** job.current_attempt)
            else:
                job.status = "dead_letter"
            WorkflowEvent.objects.create(
                job=job,
                event="attempt_failed",
                payload={"error": str(error), "attempt": attempt.number},
            )
        attempt.finished_at = timezone.now()
        attempt.save(update_fields=["status", "error", "finished_at"])
        job.save(update_fields=["status", "result", "error", "next_retry_at", "updated_at"])
        WorkflowEvent.objects.create(job=job, event=f"job_{job.status}", payload={"attempt": job.current_attempt})
        return job
