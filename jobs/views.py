from django.db import IntegrityError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Job
from .permissions import TenantRolePermission
from .serializers import JobCreateSerializer, JobSerializer
from .worker import run_job
class JobViewSet(viewsets.ModelViewSet):
    permission_classes = [TenantRolePermission]
    serializer_class = JobSerializer
    def get_queryset(self):
        return Job.objects.filter(tenant_id=self.request.headers.get("X-Tenant-Id")).prefetch_related("attempts","events")
    def create(self, request, *args, **kwargs):
        if request.headers.get("X-User-Role") != "operator": return Response({"detail":"Only operators can create jobs."}, status=403)
        serializer = JobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try: job = serializer.save(tenant_id=request.headers["X-Tenant-Id"])
        except IntegrityError: job = self.get_queryset().get(idempotency_key=request.data["idempotency_key"])
        run_job(job)
        return Response(JobSerializer(job).data, status=status.HTTP_201_CREATED)
    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        if request.headers.get("X-User-Role") != "operator": return Response({"detail":"Only operators can retry jobs."}, status=403)
        job = self.get_object()
        if job.status not in {"retrying","failed","dead_letter"}: return Response({"detail":"Only failed jobs can be retried."}, status=409)
        if job.current_attempt >= job.max_attempts:
            job.current_attempt, job.status = 0, "queued"
            job.save(update_fields=["current_attempt","status","updated_at"])
        return Response(JobSerializer(run_job(job)).data)
