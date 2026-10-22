from datetime import timedelta
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from .engine import engine
from .models import PlanChangeRequest, WorkspaceInvitation

INVITE_SALT = 'merifield.workspace.invitation.v1'


def invitation_token(invitation):
    return signing.dumps({'id': str(invitation.pk)}, salt=INVITE_SALT)


@transaction.atomic
def accept_invitation(user, token):
    try:
        value = signing.loads(token, salt=INVITE_SALT, max_age=7 * 86400)
        invitation = WorkspaceInvitation.objects.select_for_update().get(pk=value['id'])
    except (signing.BadSignature, WorkspaceInvitation.DoesNotExist, KeyError, ValueError):
        raise ValidationError('Invitation invalide ou expirée.')
    if invitation.accepted_at:
        raise ValidationError('Cette invitation a déjà été utilisée.')
    if invitation.created_at < timezone.now() - timedelta(days=7):
        raise ValidationError('Invitation expirée.')
    if not user.email or invitation.email.casefold() != user.email.casefold():
        raise PermissionDenied('Se connecter avec le compte correspondant à l’adresse invitée.')
    adapter = engine()
    account = adapter.account(invitation.created_by, invitation.owner.username)
    if not adapter.can_manage(invitation.created_by, account):
        raise PermissionDenied('L’auteur de cette invitation ne peut plus gérer cet espace.')
    adapter.add_member(invitation.created_by, account, user, invitation.role)
    invitation.accepted_at = timezone.now()
    invitation.accepted_by = user
    invitation.save(update_fields=['accepted_at', 'accepted_by'])
    return account


@transaction.atomic
def approve_request(actor, request_id):
    if not actor.is_superuser:
        raise PermissionDenied
    change = PlanChangeRequest.objects.select_for_update().select_related('owner', 'offer').get(pk=request_id)
    if change.status != PlanChangeRequest.Status.PENDING:
        raise ValidationError('Cette demande a déjà été traitée.')
    # A manual pilot grant is not a recorded payment or an automatic renewal.
    sid = engine().activate_offer(actor, change.owner, change.offer, change.seats)
    change.status = PlanChangeRequest.Status.APPROVED
    change.processed_at = timezone.now()
    change.processed_by = actor
    change.engine_subscription_id = sid
    change.save(update_fields=['status', 'processed_at', 'processed_by', 'engine_subscription_id'])
    return change
