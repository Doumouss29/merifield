from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from merifield_portal.models import Offer, PlanChangeRequest, WorkspaceInvitation
from merifield_portal.services import approve_request, invitation_token
from .fake_engine import FakeEngine


class PortalTests(TestCase):
    def setUp(self):
        FakeEngine.reset()
        User = get_user_model()
        self.alice = User.objects.create_user(username='alice', email='alice@example.invalid', password='test')
        self.bob = User.objects.create_user(username='bob', email='bob@example.invalid', password='test')
        self.admin = User.objects.create_superuser(username='admin', email='admin@example.invalid', password='test')
        self.org = FakeEngine().create_organization(self.alice, 'cabinet-alice')
        self.other = FakeEngine().create_organization(self.bob, 'cabinet-bob')
        self.offer = Offer.objects.create(code='equipe', name='Équipe', engine_plan_code='equipe')
        self.client.force_login(self.alice)

    def test_dashboard_scopes_workspace_and_projects(self):
        account = FakeEngine().account(self.alice, self.org.username)
        FakeEngine().create_project(self.alice, account, 'parcelles-alice', 'Description')
        other = FakeEngine().account(self.bob, self.other.username)
        FakeEngine().create_project(self.bob, other, 'secret-bob', 'Invisible')
        response = self.client.get('/', {'workspace': self.org.username})
        self.assertContains(response, 'parcelles-alice')
        self.assertNotContains(response, 'secret-bob')
        self.assertEqual(404, self.client.get('/', {'workspace': self.other.username}).status_code)

    def test_cross_tenant_mutations_are_rejected(self):
        for route in ['portal_new_project', 'portal_members', 'portal_offers']:
            response = self.client.post(reverse(route, args=[self.other.username]), {'name': 'malicious', 'email': self.alice.email, 'role': 'admin'})
            self.assertEqual(404, response.status_code)
        self.assertEqual(0, WorkspaceInvitation.objects.count())
        self.assertEqual(0, PlanChangeRequest.objects.count())

    def test_create_private_project_and_view(self):
        response = self.client.post(reverse('portal_new_project', args=[self.org.username]), {'name': 'mission-test', 'description': '<script>alert(1)</script>'})
        self.assertEqual(302, response.status_code)
        page = self.client.get(response.url)
        self.assertContains(page, '&lt;script&gt;')
        self.assertNotContains(page, '<script>alert(1)</script>')
        self.client.force_login(self.bob)
        self.assertEqual(404, self.client.get(response.url).status_code)

    def test_request_ignores_forged_owner_and_rejects_duplicates(self):
        url = reverse('portal_offers', args=[self.org.username])
        response = self.client.post(url, {'offer': self.offer.pk, 'cycle': 'annual', 'owner': self.other.pk})
        self.assertEqual(302, response.status_code)
        change = PlanChangeRequest.objects.get()
        self.assertEqual(self.org.pk, change.owner_id)
        self.assertEqual('annual', change.cycle)
        self.client.post(url, {'offer': self.offer.pk, 'cycle': 'monthly'})
        self.assertEqual(1, PlanChangeRequest.objects.count())

    def test_normal_user_and_staff_cannot_activate_subscription(self):
        change = PlanChangeRequest.objects.create(owner=self.org, requested_by=self.alice, offer=self.offer, cycle='monthly')
        self.assertEqual(403, self.client.post(reverse('portal_approve', args=[change.pk])).status_code)
        self.alice.is_staff = True
        self.alice.save()
        self.assertEqual(403, self.client.post(reverse('portal_approve', args=[change.pk])).status_code)
        self.assertEqual([], FakeEngine.activations)

    def test_manual_activation_is_recorded_and_not_repeated(self):
        change = PlanChangeRequest.objects.create(owner=self.org, requested_by=self.alice, offer=self.offer, cycle='monthly')
        approve_request(self.admin, change.pk)
        change.refresh_from_db()
        self.assertEqual('approved', change.status)
        self.assertEqual(self.admin.pk, change.processed_by_id)
        self.assertEqual('42', change.engine_subscription_id)
        with self.assertRaises(ValidationError):
            approve_request(self.admin, change.pk)
        self.assertEqual(1, len(FakeEngine.activations))

    def test_invitation_email_correct_account_and_single_use(self):
        response = self.client.post(reverse('portal_members', args=[self.org.username]), {'email': self.bob.email, 'role': 'member'})
        self.assertEqual(302, response.status_code)
        self.assertEqual(1, len(mail.outbox))
        self.assertIn('Mérifield Cloud', mail.outbox[0].subject)
        invitation = WorkspaceInvitation.objects.get()
        url = reverse('portal_accept_invite', args=[invitation_token(invitation)])
        self.assertEqual(403, self.client.post(url).status_code)
        self.client.force_login(self.bob)
        self.assertEqual(302, self.client.post(url).status_code)
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.accepted_at)
        self.assertEqual(200, self.client.post(url).status_code)
        self.assertEqual(1, len(FakeEngine.joined))

    def test_expired_invitation_does_not_add_member(self):
        invitation = WorkspaceInvitation.objects.create(owner=self.org, created_by=self.alice, email=self.bob.email)
        WorkspaceInvitation.objects.filter(pk=invitation.pk).update(created_at=timezone.now() - timedelta(days=8))
        self.client.force_login(self.bob)
        response = self.client.post(reverse('portal_accept_invite', args=[invitation_token(invitation)]))
        self.assertContains(response, 'expirée')
        self.assertEqual([], FakeEngine.joined)

    def test_revoked_admin_cannot_grant_old_invitation(self):
        invitation = WorkspaceInvitation.objects.create(owner=self.org, created_by=self.alice, email=self.bob.email)
        FakeEngine.disabled_managers.add(self.alice.pk)
        self.client.force_login(self.bob)
        self.assertEqual(403, self.client.post(reverse('portal_accept_invite', args=[invitation_token(invitation)])).status_code)
        self.assertEqual([], FakeEngine.joined)

    def test_login_required_and_csrf(self):
        self.client.logout()
        self.assertEqual(302, self.client.get('/').status_code)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        self.assertEqual(403, client.post(reverse('portal_new_organization'), {'username': 'new-cabinet'}).status_code)

    def test_all_portal_pages_render_and_branding_is_present(self):
        for url in ['/', reverse('portal_new_organization'), reverse('portal_new_project', args=[self.org.username]),
                    reverse('portal_members', args=[self.org.username]), reverse('portal_offers', args=[self.org.username]), reverse('portal_legal')]:
            response = self.client.get(url)
            self.assertEqual(200, response.status_code)
            self.assertContains(response, 'Mérifield')
        self.client.force_login(self.admin)
        self.assertEqual(200, self.client.get(reverse('portal_administration')).status_code)
        self.client.logout()
        self.assertEqual(200, self.client.get(reverse('account_login')).status_code)
