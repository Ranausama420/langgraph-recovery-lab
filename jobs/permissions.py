from rest_framework.permissions import BasePermission
from .context import request_context
class TenantRolePermission(BasePermission):
    def has_permission(self, request, view):
        tenant, role = request_context(request)
        if not tenant or role not in {"operator", "viewer"}:
            return False
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and role != "operator":
            return False
        return True
    def has_object_permission(self, request, view, obj):
        tenant, _ = request_context(request)
        return obj.tenant_id == tenant
