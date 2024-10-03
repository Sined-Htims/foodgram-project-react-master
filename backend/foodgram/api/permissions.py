from rest_framework import permissions
from rest_framework.request import Request


class IsAuthorPermissions(permissions.BasePermission):
    def has_object_permission(self, request: Request, view, obj):
        return obj.author == request.user
