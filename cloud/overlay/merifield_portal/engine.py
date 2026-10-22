"""Adapter to the pinned QFieldCloud engine. No copy of auth/quota logic."""
from types import SimpleNamespace
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.utils import timezone
from django.utils.module_loading import import_string


def engine():
    return import_string(getattr(settings, 'MERIFIELD_ENGINE', 'merifield_portal.engine.QfcEngine'))()


class QfcEngine:
    def accounts(self, user):
        from qfieldcloud.core.models import Organization
        return [user] + list(Organization.objects.of_user(user).order_by('username'))

    def account(self, user, username):
        for account in self.accounts(user):
            if account.username == username:
                return account
        raise Http404('Espace introuvable.')

    def can_manage(self, user, account):
        if account.pk == user.pk:
            return True
        from qfieldcloud.core.models import Organization
        organization = Organization.objects.filter(pk=account.pk).first()
        if not organization:
            return False
        return (organization.organization_owner_id == user.pk or
                Organization.objects.of_user(user).filter(pk=account.pk, membership_role='admin').exists())

    def summary(self, account):
        subscription = account.useraccount.current_subscription
        used = account.useraccount.storage_used_bytes
        total = subscription.active_storage_total_bytes
        return dict(used=used, total=total, percent=min(100, round(used * 100 / total)) if total else 100,
                    plan=subscription.plan.display_name, members=subscription.organization_members_count if account.is_organization else 1,
                    status='Actif' if subscription.is_active else 'Inactif', is_org=account.is_organization)

    def projects(self, user, account):
        from qfieldcloud.project.models import Project
        return Project.objects.for_user(user, skip_invalid=True).filter(owner_id=account.pk).order_by('-updated_at')

    def project(self, user, project_id):
        from qfieldcloud.project.models import Project
        try:
            return Project.objects.for_user(user, skip_invalid=True).get(pk=project_id)
        except Project.DoesNotExist:
            raise Http404('Projet introuvable.')

    def jobs(self, user, project):
        from qfieldcloud.core.models import Job
        from qfieldcloud.core.permissions_utils import can_read_jobs
        if not can_read_jobs(user, project):
            return []
        return Job.objects.filter(project=project).for_user(user)[:30]

    def files(self, user, project):
        from qfieldcloud.core.permissions_utils import can_read_files
        if not can_read_files(user, project):
            return []
        return project.project_files.select_related('latest_version').order_by('name')[:200]

    def download(self, user, project, filename):
        from qfieldcloud.filestorage.views import FileCrudView
        from rest_framework.test import APIRequestFactory, force_authenticate
        request = APIRequestFactory().get('/')
        force_authenticate(request, user=user)
        response = FileCrudView.as_view()(request, project_id=project.pk, filename=filename)
        if hasattr(response, 'render'):
            response.render()
        return response

    def can_create_project(self, user, account):
        from qfieldcloud.core.permissions_utils import can_create_project
        return can_create_project(user, account)

    def create_organization(self, user, username):
        from qfieldcloud.core.models import Organization
        from qfieldcloud.core.permissions_utils import can_create_organizations
        from django.db import transaction
        if not can_create_organizations(user):
            raise PermissionDenied
        with transaction.atomic():
            organization = Organization(username=username, organization_owner=user, created_by=user)
            organization.set_unusable_password()
            organization.full_clean(exclude=['password'])
            organization.save()
        return organization

    def create_project(self, user, account, name, description):
        # Call the engine's API view so serializer checks and quota enforcement
        # remain identical to mobile/plugin requests, without a network hop.
        from qfieldcloud.project.views import ProjectViewSet
        from rest_framework.test import APIRequestFactory, force_authenticate
        if not self.can_create_project(user, account):
            raise PermissionDenied
        request = APIRequestFactory().post('/api/v1/projects/', {
            'owner': account.username, 'name': name, 'description': description, 'private': True,
        }, format='json')
        force_authenticate(request, user=user)
        response = ProjectViewSet.as_view({'post': 'create'})(request)
        if response.status_code >= 400:
            raise ValidationError(str(response.data))
        return self.project(user, response.data['id'])

    def members(self, user, account):
        if not account.is_organization:
            return []
        from qfieldcloud.core.models import OrganizationMember
        return OrganizationMember.objects.filter(organization_id=account.pk).select_related('member')

    def verified_email(self, user, email):
        from allauth.account.models import EmailAddress
        return EmailAddress.objects.filter(user=user, email__iexact=email, verified=True).exists()

    def add_member(self, actor, account, member, role):
        from qfieldcloud.core.models import OrganizationMember, Organization
        if not account.is_organization or not self.can_manage(actor, account):
            raise PermissionDenied
        from django.db import transaction
        # Serialize seat checks with other portal changes on this organization.
        with transaction.atomic():
            org = Organization.objects.select_for_update().get(pk=account.pk)
            if org.organization_owner_id == member.pk:
                return None
            from qfieldcloud.subscription.exceptions import ReachedMaxOrganizationMembersError
            try:
                record, created = OrganizationMember.objects.get_or_create(
                    organization=org, member=member,
                    defaults={'role': role, 'created_by': actor, 'updated_by': actor})
            except ReachedMaxOrganizationMembersError:
                raise ValidationError('Le nombre de membres autorisé par cette offre est atteint. Demander une extension à l’administrateur.')
            # An old invitation must never upgrade an existing member's role.
            return record

    def offer_limits(self, code):
        from qfieldcloud.subscription.models import Plan
        plan = Plan.objects.filter(code=code).first()
        if not plan:
            return None
        return {'storage_mb': plan.storage_mb, 'members': plan.max_organization_members,
                'external_db': plan.is_external_db_supported, 'versions': plan.storage_keep_versions, 'user_type': plan.user_type}

    def activate_offer(self, actor, account, offer, seats):
        from qfieldcloud.core.models import UserAccount, Person
        from qfieldcloud.subscription.models import Plan, get_subscription_model
        from django.db import transaction
        if not actor.is_superuser:
            raise PermissionDenied
        plan = Plan.objects.filter(code=offer.engine_plan_code).first()
        if plan is None:
            raise ValidationError('Le plan technique de cette offre est introuvable.')
        if plan.user_type != account.type:
            raise ValidationError('Cette offre ne correspond pas au type de compte.')
        if not plan.is_seat_based and seats != 1:
            raise ValidationError('Cette offre utilise un forfait global, pas un tarif par utilisateur.')
        with transaction.atomic():
            locked = UserAccount.objects.select_for_update().get(pk=account.pk)
            created = get_subscription_model().create_subscription(
                account=locked, regular_plan=plan, created_by=Person.objects.get(pk=actor.pk),
                active_since=timezone.now())
            if plan.is_seat_based:
                created.purchased_seats = seats
                created.save(update_fields=['purchased_seats'])
            return str(created.pk)
