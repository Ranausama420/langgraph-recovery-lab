import uuid
from django.db import models

class Job(models.Model):
    STATUS = [("queued","Queued"),("running","Running"),("retrying","Retrying"),("completed","Completed"),("failed","Failed"),("dead_letter","Dead letter")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=100, db_index=True)
    task = models.CharField(max_length=200)
    tool = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=STATUS, default="queued")
    max_attempts = models.PositiveIntegerField(default=3)
    current_attempt = models.PositiveIntegerField(default=0)
    idempotency_key = models.CharField(max_length=200)
    result = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant_id","idempotency_key"], name="unique_tenant_idempotency")]
        ordering = ["-created_at"]

class Attempt(models.Model):
    job = models.ForeignKey(Job, related_name="attempts", on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    status = models.CharField(max_length=20)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)

class WorkflowEvent(models.Model):
    job = models.ForeignKey(Job, related_name="events", on_delete=models.CASCADE)
    event = models.CharField(max_length=80)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
