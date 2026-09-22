from rest_framework.permissions import BasePermission


class IsDriver(BasePermission):
    message = 'User must be a driver.'

    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'role', None) == 'driver')


class IsDriverOrOwner(BasePermission):
    message = 'User must be a driver or taxi owner.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and getattr(request.user, 'role', None) in {'driver', 'owner'}
        )


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return bool(request.user and request.user.is_staff)


class IsOwnerOrAdmin(BasePermission):
    message = 'Must be owner or admin.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        owner = getattr(obj, 'owner', None) or getattr(obj, 'user', None) or getattr(obj, 'driver', None)
        return owner == request.user
