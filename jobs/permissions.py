from rest_framework.permissions import BasePermission
class TenantRolePermission(BasePermission):
    def has_permission(self, request, view):
        return request.headers.get("X-Tenant-Id") and request.headers.get("X-User-Role") in {"operator","viewer"}
    def has_object_permission(self, request, view, obj):
        return obj.tenant_id == request.headers.get("X-Tenant-Id")
