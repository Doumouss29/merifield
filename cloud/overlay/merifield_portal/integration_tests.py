"""Run inside the real engine container with PostGIS, not SQLite/fake_engine."""
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.http import Http404
from django.test import TransactionTestCase, Client
from django.urls import reverse
from merifield_portal.engine import QfcEngine
from merifield_portal.models import Offer, PlanChangeRequest
from merifield_portal.services import approve_request


class EngineIntegrationTests(TransactionTestCase):
    def setUp(self):
        from qfieldcloud.core.models import Person
        call_command('merifield_seed', verbosity=0)
        self.alice = Person.objects.create_user(username='mf_alice', email='mf_alice@example.invalid', password='Long-test-password-93!')
        self.bob = Person.objects.create_user(username='mf_bob', email='mf_bob@example.invalid', password='Long-test-password-93!')
        self.admin = Person.objects.create_superuser(username='mf_admin', email='mf_admin@example.invalid', password='Long-test-password-93!')
        self.adapter = QfcEngine()
        self.org = self.adapter.create_organization(self.alice, 'mf_cabinet')

    def test_real_organization_role_view_and_private_project(self):
        self.assertEqual(self.org.pk, self.adapter.account(self.alice, self.org.username).pk)
        with self.assertRaises(Http404):
            self.adapter.account(self.bob, self.org.username)
        project = self.adapter.create_project(self.alice, self.org, 'signature-test', 'Test réel')
        self.assertFalse(project.is_public)
        self.assertEqual(self.org.pk, project.owner_id)
        with self.assertRaises(Http404):
            self.adapter.project(self.bob, project.pk)
        client = Client()
        client.force_login(self.alice)
        self.assertEqual(200, client.get('/', {'workspace': self.org.username}, secure=True).status_code)
        self.assertEqual(200, client.get(reverse('portal_project', args=[project.pk]), secure=True).status_code)

    def test_offer_activation_changes_engine_storage_limit(self):
        offer = Offer.objects.get(code='merifield_equipe')
        request = PlanChangeRequest.objects.create(owner=self.org, requested_by=self.alice, offer=offer, cycle='annual')
        approve_request(self.admin, request.pk)
        from qfieldcloud.core.models import Organization
        fresh = Organization.objects.get(pk=self.org.pk)
        self.assertEqual('merifield_equipe', fresh.useraccount.current_subscription.plan.code)
        self.assertEqual(50_000_000_000, fresh.useraccount.current_subscription.active_storage_total_bytes)
        with self.assertRaises(ValidationError):
            approve_request(self.admin, request.pk)

    def test_seed_does_not_overwrite_customized_quota_or_price(self):
        from qfieldcloud.subscription.models import Plan
        Plan.objects.filter(code='merifield_equipe').update(storage_mb=12345)
        Offer.objects.filter(code='merifield_equipe').update(monthly_price=12000)
        call_command('merifield_seed', verbosity=0)
        self.assertEqual(12345, Plan.objects.get(code='merifield_equipe').storage_mb)
        self.assertEqual(12000, Offer.objects.get(code='merifield_equipe').monthly_price)

    def test_verified_invitation_and_real_member_quota(self):
        from allauth.account.models import EmailAddress
        from merifield_portal.models import WorkspaceInvitation
        from merifield_portal.services import accept_invitation, invitation_token
        EmailAddress.objects.create(user=self.bob, email=self.bob.email, verified=True, primary=True)
        invitation = WorkspaceInvitation.objects.create(owner=self.org, created_by=self.alice, email=self.bob.email)
        accept_invitation(self.bob, invitation_token(invitation))
        self.assertEqual(self.org.pk, self.adapter.account(self.bob, self.org.username).pk)
        with self.assertRaises(ValidationError):
            self.adapter.add_member(self.alice, self.org, self.admin, 'member')
