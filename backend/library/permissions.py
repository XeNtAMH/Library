from rest_framework.permissions import BasePermission, SAFE_METHODS


def role_for(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return "admin"
    profile = getattr(user, "library_profile", None)
    return profile.role if profile else None


def is_staff_member(user):
    return role_for(user) in {"admin", "librarian"}


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return role_for(request.user) == "admin"


class IsStaff(BasePermission):
    def has_permission(self, request, view):
        return is_staff_member(request.user)


class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or is_staff_member(request.user)