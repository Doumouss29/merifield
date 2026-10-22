from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .engine import engine
from .forms import ChangeForm, InvitationForm, OrganizationForm, ProjectForm
from .models import Offer, PlanChangeRequest, WorkspaceInvitation
from .services import invitation_token, accept_invitation, approve_request


def notice_error(request, error):
    messages.error(request, '; '.join(error.messages) if isinstance(error, ValidationError) else str(error))


@login_required
def home(request):
    adapter = engine()
    accounts = adapter.accounts(request.user)
    if not accounts:
        raise PermissionDenied
    selected = request.GET.get('workspace')
    account = adapter.account(request.user, selected) if selected else accounts[0]
    projects = adapter.projects(request.user, account)
    query = request.GET.get('q', '').strip()
    if query:
        projects = projects.filter(name__icontains=query)
    # Limit rendering without changing the scope used for authorization.
    count = projects.count()
    return render(request, 'merifield/dashboard.html', {
        'accounts': accounts, 'workspace': account, 'summary': adapter.summary(account),
        'projects': projects[:100], 'project_count': count, 'query': query,
        'can_manage': adapter.can_manage(request.user, account),
        'can_create': adapter.can_create_project(request.user, account),
    })


@login_required
def new_organization(request):
    form = OrganizationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            organization = engine().create_organization(request.user, form.cleaned_data['username'])
            messages.success(request, 'L’espace entreprise est créé.')
            return redirect(reverse('index') + '?workspace=' + organization.username)
        except (ValidationError, IntegrityError) as error:
            form.add_error(None, 'Cet identifiant existe déjà ou ne peut pas être utilisé.' if isinstance(error, IntegrityError) else error)
    return render(request, 'merifield/form.html', {'form': form, 'title': 'Créer un espace entreprise', 'intro': 'Un espace sépare les projets, les membres et le stockage de chaque entreprise.'})


@login_required
def new_project(request, workspace):
    adapter = engine()
    account = adapter.account(request.user, workspace)
    if not adapter.can_create_project(request.user, account):
        raise PermissionDenied
    form = ProjectForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            project = adapter.create_project(request.user, account, **form.cleaned_data)
            messages.success(request, 'Projet créé. Publiez maintenant ses données depuis Mérifield Sync dans QGIS.')
            return redirect('portal_project', project_id=project.pk)
        except (ValidationError, IntegrityError) as error:
            form.add_error(None, 'Ce nom de projet est déjà utilisé.' if isinstance(error, IntegrityError) else error)
    return render(request, 'merifield/form.html', {'form': form, 'workspace': account, 'title': 'Nouveau projet', 'intro': 'Le projet est privé. Les fichiers et le formulaire sont publiés depuis QGIS.'})


@login_required
def project_detail(request, project_id):
    adapter = engine()
    project = adapter.project(request.user, project_id)
    return render(request, 'merifield/project.html', {'project': project, 'workspace': project.owner,
                                                    'jobs': adapter.jobs(request.user, project), 'files': adapter.files(request.user, project)})


@login_required
def members(request, workspace):
    adapter = engine()
    account = adapter.account(request.user, workspace)
    if not adapter.can_manage(request.user, account) or not adapter.summary(account)['is_org']:
        raise PermissionDenied
    form = InvitationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                invite = form.save(commit=False)
                invite.owner = account
                invite.created_by = request.user
                invite.email = invite.email.strip().lower()
                invite.save()
                link = request.build_absolute_uri(reverse('portal_accept_invite', args=[invitation_token(invite)]))
                send_mail('Invitation — Mérifield Cloud',
                    f'Vous êtes invité à rejoindre l’espace {account.username} sur Mérifield Cloud.\n\n'
                    f'Connectez-vous avec cette adresse e-mail puis acceptez l’invitation :\n{link}\n\nCe lien expire dans 7 jours.',
                    settings.DEFAULT_FROM_EMAIL, [invite.email], fail_silently=False)
            messages.success(request, 'Invitation envoyée. Le membre rejoindra cet espace après acceptation.')
            return redirect('portal_members', workspace=workspace)
        except Exception as error:
            # Email transport failure: rollback invitation and keep entered form.
            if isinstance(error, PermissionDenied):
                raise
            form.add_error(None, 'L’invitation n’a pas pu être envoyée. Vérifier le service e-mail ou réessayer.')
    return render(request, 'merifield/members.html', {
        'workspace': account, 'form': form, 'members': adapter.members(request.user, account),
        'invitations': WorkspaceInvitation.objects.filter(owner=account)[:50],
    })


@login_required
def accept_invite(request, token):
    error = None
    if request.method == 'POST':
        try:
            account = accept_invitation(request.user, token)
            messages.success(request, 'Vous avez rejoint l’espace entreprise.')
            return redirect(reverse('index') + '?workspace=' + account.username)
        except ValidationError as exc:
            error = '; '.join(exc.messages)
    return render(request, 'merifield/accept.html', {'token': token, 'error': error})


@login_required
def offers(request, workspace):
    adapter = engine()
    account = adapter.account(request.user, workspace)
    if not adapter.can_manage(request.user, account):
        raise PermissionDenied
    form = ChangeForm(request.POST or None)
    visible = Offer.objects.filter(published=True)
    eligible_ids = [offer.pk for offer in visible
                    if (adapter.offer_limits(offer.engine_plan_code) or {}).get('user_type') == account.type]
    form.fields['offer'].queryset = visible.filter(pk__in=eligible_ids)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                change = form.save(commit=False)
                change.owner = account
                change.requested_by = request.user
                change.save()
            messages.success(request, 'Demande transmise. L’offre sera activée après validation manuelle ; aucun paiement n’a été prélevé.')
            return redirect('portal_offers', workspace=workspace)
        except IntegrityError:
            form.add_error(None, 'Une demande est déjà en attente pour cet espace.')
    catalogue = [{'offer': offer, 'limits': adapter.offer_limits(offer.engine_plan_code)} for offer in form.fields['offer'].queryset]
    return render(request, 'merifield/offers.html', {'workspace': account, 'form': form, 'catalogue': catalogue,
        'summary': adapter.summary(account), 'requests': PlanChangeRequest.objects.filter(owner=account)[:20]})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def administration(request):
    return render(request, 'merifield/administration.html', {
        'requests': PlanChangeRequest.objects.select_related('owner', 'offer', 'requested_by')[:100],
        'pending_count': PlanChangeRequest.objects.filter(status='pending').count(),
        'offers': Offer.objects.all(),
    })


@login_required
@require_POST
def approve(request, request_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    try:
        approve_request(request.user, request_id)
        messages.success(request, 'L’offre a été activée dans le moteur de synchronisation. Aucun encaissement automatique.')
    except ValidationError as error:
        notice_error(request, error)
    return redirect('portal_administration')


@login_required
@require_POST
def reject(request, request_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    with transaction.atomic():
        change = get_object_or_404(PlanChangeRequest.objects.select_for_update(), pk=request_id)
        if change.status == 'pending':
            change.status = 'rejected'
            change.processed_at = timezone.now()
            change.processed_by = request.user
            change.save(update_fields=['status', 'processed_at', 'processed_by'])
    return redirect('portal_administration')


def legal(request):
    return render(request, 'merifield/legal.html')


def health(request):
    # Readiness stays at the engine's /api/v1/status/ endpoint.
    return HttpResponse('Mérifield Cloud', content_type='text/plain')


@login_required
def download_file(request, project_id, filename):
    adapter = engine()
    project = adapter.project(request.user, project_id)
    return adapter.download(request.user, project, filename)
