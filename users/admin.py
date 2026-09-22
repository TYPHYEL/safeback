from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, DriverProfile


@admin.action(description='Approuver les profils sélectionnés')
def approve_selected(modeladmin, request, queryset):
    queryset.update(verified=True)
    modeladmin.message_user(request, f'{queryset.count()} profil(s) approuvé(s).')


@admin.action(description='Rejeter les profils sélectionnés')
def reject_selected(modeladmin, request, queryset):
    queryset.update(verified=False)
    modeladmin.message_user(request, f'{queryset.count()} profil(s) rejeté(s).')


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Role", {"fields": ("role",)}),
    )


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_number', 'verified', 'is_active')
    list_filter = ('verified', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'license_number', 'plate_number')
    actions = (approve_selected, reject_selected)
