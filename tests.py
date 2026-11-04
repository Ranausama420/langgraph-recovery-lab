from django.test import TestCase
from rest_framework.test import APIClient
from jobs.models import Job

class TenantIsolationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.operator = {"HTTP_X_TENANT_ID":"acme", "HTTP_X_USER_ROLE":"operator"}
        self.viewer = {"HTTP_X_TENANT_ID":"acme", "HTTP_X_USER_ROLE":"viewer"}
    def test_idempotent_retry_and_roles(self):
        payload = {"task":"send report", "tool":"unstable_email", "idempotency_key":"job-1", "max_attempts":3}
        first = self.client.post("/api/jobs/", payload, format="json", **self.operator)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["status"], "retrying")
        duplicate = self.client.post("/api/jobs/", payload, format="json", **self.operator)
        self.assertEqual(duplicate.json()["id"], first.json()["id"])
        forbidden = self.client.post("/api/jobs/", {**payload,"idempotency_key":"job-2"}, format="json", **self.viewer)
        self.assertEqual(forbidden.status_code, 403)
    def test_tenant_cannot_read_other_tenant(self):
        job = Job.objects.create(tenant_id="other", task="x", tool="report", idempotency_key="x")
        self.assertEqual(self.client.get(f"/api/jobs/{job.id}/", **self.viewer).status_code, 404)
