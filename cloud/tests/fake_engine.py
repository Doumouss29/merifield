"""In-process adapter used only by local view/security tests, never production."""
import uuid
from types import SimpleNamespace
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.contrib.auth import get_user_model


class Rows(list):
    def count(self):
        return len(self)
    def filter(self, **kwargs):
        return Rows([p for p in self if kwargs.get('name__icontains', '').lower() in p.name.lower()])


class FakeEngine:
    organizations = {}
    records = {}
    activations = []
    joined = []
    disabled_managers = set()
    unverified_users = set()

    @classmethod
    def reset(cls):
        cls.organizations = {}
        cls.records = {}
        cls.activations = []
        cls.joined = []
        cls.disabled_managers = set()
        cls.unverified_users = set()

    def accounts(self, user):
        user.type = 1
        user.is_organization = False
        rows = [user]
        for org_id, owner_id in self.organizations.items():
            if owner_id == user.pk or (org_id, user.pk) in self.joined:
                org = get_user_model().objects.get(pk=org_id)
                org.is_organization = True
                org.type = 2
                rows.append(org)
        return rows

    def account(self, user, username):
        for account in self.accounts(user):
            if account.username == username:
                return account
        raise Http404

    def can_manage(self, user, account):
        return user.pk not in self.disabled_managers and (user.pk == account.pk or self.organizations.get(account.pk) == user.pk)

    can_create_project = can_manage

    def summary(self, account):
        return {'used': 100, 'total': 1000000, 'percent': 1, 'plan': 'Pilote', 'status': 'Actif', 'members': 1,
                'is_org': account.pk in self.organizations}

    def projects(self, user, account):
        return Rows([p for p in self.records.values() if p.owner.pk == account.pk])

    def project(self, user, pk):
        project = self.records.get(str(pk))
        if project and project.owner.username in [a.username for a in self.accounts(user)]:
            return project
        raise Http404

    def files(self, user, project):
        return []

    def jobs(self, user, project):
        return []

    def create_organization(self, user, username):
        org = get_user_model().objects.create(username=username)
        self.organizations[org.pk] = user.pk
        return org

    def create_project(self, user, account, name, description):
        if not self.can_manage(user, account):
            raise PermissionDenied
        project = SimpleNamespace(pk=uuid.uuid4(), name=name, description=description, owner=account,
                                  is_public=False, file_storage_bytes=0, updated_at=timezone.now())
        self.records[str(project.pk)] = project
        return project

    def members(self, user, account):
        return []

    def verified_email(self, user, email):
        return user.pk not in self.unverified_users

    def add_member(self, actor, account, member, role):
        if not self.can_manage(actor, account):
            raise PermissionDenied
        self.joined.append((account.pk, member.pk))

    def offer_limits(self, code):
        return {'storage_mb': 1000, 'members': 5, 'external_db': True, 'versions': 10, 'user_type': 2}

    def activate_offer(self, actor, account, offer, seats):
        if not actor.is_superuser:
            raise PermissionDenied
        self.activations.append((account.pk, offer.engine_plan_code, seats))
        return '42'
