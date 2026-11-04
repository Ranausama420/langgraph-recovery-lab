from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from .models import Job, WorkflowEvent
from .context import request_context
from .permissions import TenantRolePermission
from .serializers import EventSerializer, JobCreateSerializer, JobSerializer
from .worker import run_job


class JobPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def dispatch_job(job):
    if settings.ASYNC_JOBS:
        from .tasks import execute_job
        execute_job.delay(str(job.id))
        return job
    return run_job(job)


class JobViewSet(viewsets.ModelViewSet):
    permission_classes = [TenantRolePermission]
    serializer_class = JobSerializer
    pagination_class = JobPagination

    def get_queryset(self):
        tenant, _ = request_context(self.request)
        queryset = Job.objects.filter(
            tenant_id=tenant
        ).prefetch_related("attempts", "events")
        status_filter = self.request.query_params.get("status")
        tool = self.request.query_params.get("tool")
        search = self.request.query_params.get("search")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if tool:
            queryset = queryset.filter(tool=tool)
        if search:
            queryset = queryset.filter(Q(task__icontains=search) | Q(idempotency_key__icontains=search))
        ordering = self.request.query_params.get("ordering", "-created_at")
        allowed_ordering = {"created_at", "-created_at", "updated_at", "-updated_at", "status", "task"}
        return queryset.order_by(ordering if ordering in allowed_ordering else "-created_at")

    def get_serializer_class(self):
        return JobCreateSerializer if self.action == "create" else JobSerializer

    def create(self, request, *args, **kwargs):
        tenant, role = request_context(request)
        if role != "operator":
            return Response({"detail": "Only operators can create jobs."}, status=403)
        serializer = JobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = serializer.validated_data["idempotency_key"]
        existing = self.get_queryset().filter(idempotency_key=idempotency_key).first()
        if existing:
            return Response(JobSerializer(existing).data, status=status.HTTP_200_OK)
        try:
            with transaction.atomic():
                job = serializer.save(tenant_id=tenant)
        except IntegrityError:
            job = self.get_queryset().get(idempotency_key=idempotency_key)
            return Response(JobSerializer(job).data, status=status.HTTP_200_OK)
        dispatch_job(job)
        return Response(JobSerializer(job).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        queryset = self.get_queryset()
        counts = queryset.values("status").annotate(count=Count("id"))
        by_status = {row["status"]: row["count"] for row in counts}
        return Response({
            "total": queryset.count(),
            "completed": by_status.get("completed", 0),
            "dead_letter": by_status.get("dead_letter", 0),
            "retrying": by_status.get("retrying", 0),
            "running": by_status.get("running", 0),
            "queued": by_status.get("queued", 0),
            "by_tool": {
                row["tool"]: row["count"]
                for row in queryset.values("tool").annotate(count=Count("id"))
            },
        })

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        job = self.get_object()
        return Response(EventSerializer(job.events.all(), many=True).data)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        _, role = request_context(request)
        if role != "operator":
            return Response({"detail": "Only operators can retry jobs."}, status=403)
        job = self.get_object()
        if job.status not in {"retrying", "failed", "dead_letter"}:
            return Response({"detail": "Only failed jobs can be retried."}, status=409)
        if job.current_attempt >= job.max_attempts:
            job.max_attempts += 3
            job.status = "queued"
            job.next_retry_at = None
            job.save(update_fields=["max_attempts", "status", "next_retry_at", "updated_at"])
        WorkflowEvent.objects.create(job=job, event="manual_retry_requested", payload={"attempt": job.current_attempt})
        return Response(JobSerializer(dispatch_job(job)).data)
