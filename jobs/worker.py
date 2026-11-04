from django.utils import timezone
from .models import Attempt, Job, WorkflowEvent
def run_job(job):
    job.current_attempt += 1
    job.status = "running"
    job.save(update_fields=["current_attempt","status","updated_at"])
    attempt = Attempt.objects.create(job=job, number=job.current_attempt, status="running")
    WorkflowEvent.objects.create(job=job, event="attempt_started", payload={"attempt": attempt.number})
    try:
        if job.tool == "validation": raise RuntimeError("Permanent validation failure")
        if job.tool == "unstable_email" and job.current_attempt == 1: raise RuntimeError("Temporary email provider timeout")
        job.status, job.result, attempt.status = "completed", {"message": f"{job.tool} completed", "attempt": job.current_attempt}, "completed"
    except RuntimeError as error:
        job.error, attempt.status, attempt.error = str(error), "failed", str(error)
        job.status = "retrying" if job.current_attempt < job.max_attempts else "dead_letter"
        WorkflowEvent.objects.create(job=job, event="attempt_failed", payload={"error": str(error), "attempt": attempt.number})
    attempt.finished_at = timezone.now()
    attempt.save(update_fields=["status","error","finished_at"])
    job.save(update_fields=["status","result","error","updated_at"])
    WorkflowEvent.objects.create(job=job, event=f"job_{job.status}", payload={"attempt": job.current_attempt})
    return job
