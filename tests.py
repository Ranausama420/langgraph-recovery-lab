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
        self.assertEqual(len(Job.objects.get(pk=first.json()["id"]).attempts.all()), 1)
        forbidden = self.client.post("/api/jobs/", {**payload,"idempotency_key":"job-2"}, format="json", **self.viewer)
        self.assertEqual(forbidden.status_code, 403)

    def test_filters_stats_and_timeline(self):
        payload = {"task":"send report", "tool":"report", "idempotency_key":"job-stats", "max_attempts":3}
        created = self.client.post("/api/jobs/", payload, format="json", **self.operator)
        self.assertEqual(created.status_code, 201)
        listing = self.client.get("/api/jobs/?status=completed&search=send", **self.viewer)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["count"], 1)
        stats = self.client.get("/api/jobs/stats/", **self.viewer)
        self.assertEqual(stats.status_code, 200)
        self.assertEqual(stats.json()["completed"], 1)
        timeline = self.client.get(f"/api/jobs/{created.json()['id']}/timeline/", **self.viewer)
        self.assertEqual(timeline.status_code, 200)
        self.assertEqual(timeline.json()[-1]["event"], "job_completed")

    def test_invalid_job_input_is_rejected(self):
        response = self.client.post(
            "/api/jobs/",
            {"task":"", "tool":"unknown", "idempotency_key":"bad", "max_attempts":99},
            format="json",
            **self.operator,
        )
        self.assertEqual(response.status_code, 400)
    def test_tenant_cannot_read_other_tenant(self):
        job = Job.objects.create(tenant_id="other", task="x", tool="report", idempotency_key="x")
        self.assertEqual(self.client.get(f"/api/jobs/{job.id}/", **self.viewer).status_code, 404)
