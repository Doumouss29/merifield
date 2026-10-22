from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import Offer, PlanChangeRequest, WorkspaceInvitation
from .services import approve_request


class SuperuserOnly(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission


class OfferAdmin(SuperuserOnly):
    list_display = ['name', 'engine_plan_code', 'monthly_price', 'annual_price', 'currency', 'published']
    list_editable = ['published']
    search_fields = ['name', 'code']


class RequestAdmin(SuperuserOnly):
    list_display = ['owner', 'offer', 'cycle', 'status', 'created_at', 'processed_by']
    list_filter = ['status', 'cycle']
    readonly_fields = [f.name for f in PlanChangeRequest._meta.fields]
    actions = ['activate']

    def has_add_permission(self, request):
        return False

    @admin.action(description='Activer manuellement les offres sélectionnées (aucun encaissement)')
    def activate(self, request, queryset):
        for change in queryset:
            try:
                approve_request(request.user, change.pk)
            except ValidationError as error:
                self.message_user(request, str(error), messages.WARNING)


class InvitationAdmin(SuperuserOnly):
    list_display = ['owner', 'email', 'role', 'created_at', 'accepted_at']
    readonly_fields = [f.name for f in WorkspaceInvitation._meta.fields]

    def has_add_permission(self, request):
        return False


def register_with(site):
    for model, model_admin in [(Offer, OfferAdmin), (PlanChangeRequest, RequestAdmin), (WorkspaceInvitation, InvitationAdmin)]:
        if not site.is_registered(model):
            site.register(model, model_admin)


# Do not import the engine admin while Django is still discovering apps:
# it needs rest_framework.authtoken.admin to register TokenProxy first.
register_with(admin.site)
