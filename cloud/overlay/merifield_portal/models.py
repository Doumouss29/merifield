from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Offer(models.Model):
    """Commercial labels reference an existing engine plan, never a second quota."""
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    engine_plan_code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    annual_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3, choices=[('XOF', 'FCFA'), ('EUR', 'EUR')], default='XOF')
    published = models.BooleanField(default=True)
    ordering = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordering', 'name']

    def __str__(self):
        return self.name


class PlanChangeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'À traiter'
        APPROVED = 'approved', 'Activé manuellement'
        REJECTED = 'rejected', 'Refusé'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    offer = models.ForeignKey(Offer, on_delete=models.PROTECT)
    cycle = models.CharField(max_length=10, choices=[('monthly', 'Mensuel'), ('annual', 'Annuel')])
    seats = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    engine_subscription_id = models.CharField(max_length=80, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['owner'], condition=Q(status='pending'), name='merifield_one_pending_change_per_owner')]


class WorkspaceInvitation(models.Model):
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    email = models.EmailField()
    role = models.CharField(max_length=10, choices=[('admin', 'Administrateur'), ('creator', 'Créateur de projets'), ('member', 'Membre')], default='member')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        ordering = ['-created_at']
