from celery import shared_task

from .models import Job
from .worker import run_job


@shared_task(bind=True, name="jobs.execute_job", max_retries=0)
def execute_job(self, job_id):
    """Run a job outside the request and schedule its next retry when needed."""
    job = Job.objects.get(pk=job_id)
    run_job(job)
    if job.status == "retrying" and job.next_retry_at:
        execute_job.apply_async((str(job.id),), eta=job.next_retry_at)
    return str(job.id)
