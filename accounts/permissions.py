from rest_framework import permissions

ADMIN_ROLES = ("admin",)
STAFF_ROLES = ("rep", "admin")


def is_admin(user) -> bool:
    return bool(user and (user.role in ADMIN_ROLES or user.is_superuser))


class IsRepOrAdmin(permissions.BasePermission):
    """Anyone authenticated may read; only reps and admins may write."""

    message = "Only course reps and admins may modify this resource."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.role in STAFF_ROLES)


class IsOwningRepOrAdmin(IsRepOrAdmin):
    """Writes are further restricted to the rep who owns the object.

    Without an object-level check, `IsRepOrAdmin` let any authenticated rep
    PUT or DELETE another rep's course or handout just by knowing its id.

    `owner_field` is a dotted path from the object to its owning user.
    """

    owner_field = "rep"

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if is_admin(request.user):
            return True

        owner = obj
        for part in getattr(view, "owner_field", self.owner_field).split("."):
            owner = getattr(owner, part, None)
            if owner is None:
                return False
        return owner == request.user
