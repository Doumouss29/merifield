from django.core.management.base import BaseCommand
from django.db import transaction
from merifield_portal.models import Offer


class Command(BaseCommand):
    help = 'Créer les offres pilotes Mérifield sans écraser les modifications des administrateurs.'

    @transaction.atomic
    def handle(self, *args, **options):
        from django.conf import settings
        from django.contrib.sites.models import Site
        from urllib.parse import urlsplit
        host = urlsplit(settings.MERIFIELD_PUBLIC_URL).hostname
        Site.objects.update_or_create(pk=settings.SITE_ID, defaults={'domain': host, 'name': 'Mérifield Cloud'})
        from qfieldcloud.core.models import User
        from qfieldcloud.subscription.models import Plan, SubscriptionStatus
        defaults = [
            ('merifield_personal', 'Espace personnel', 1000, 0, User.Type.PERSON, True, False, 'Votre espace de départ pour préparer vos premières collectes.'),
            ('merifield_individuel', 'Professionnel individuel', 10000, 0, User.Type.PERSON, False, True, 'Pour vos missions et vos projets personnels.'),
            ('merifield_decouverte', 'Découverte', 1000, 2, User.Type.ORGANIZATION, True, True, 'Pour découvrir la collecte en petite équipe.'),
            ('merifield_professionnel', 'Professionnel', 10000, 5, User.Type.ORGANIZATION, False, True, 'Pour un cabinet et ses missions terrain.'),
            ('merifield_equipe', 'Équipe', 50000, 20, User.Type.ORGANIZATION, False, True, 'Pour coordonner plusieurs équipes de collecte.'),
            ('merifield_entreprise', 'Entreprise', 100000, 100, User.Type.ORGANIZATION, False, True, 'Une base de configuration à adapter avec votre organisation.'),
        ]
        for index, (code, name, storage, members, user_type, is_default, public, description) in enumerate(defaults):
            plan, created = Plan.objects.get_or_create(code=code, defaults={
                'display_name': name, 'storage_mb': storage, 'user_type': user_type,
                'storage_keep_versions': 10, 'max_organization_members': members,
                'storage_threshold_warning_bytes': storage * 100_000,
                'storage_threshold_critical_bytes': storage * 20_000,
                'is_public': public, 'is_default': False, 'is_premium': True,
                'is_external_db_supported': True, 'is_seat_based': False,
                'initial_subscription_status': SubscriptionStatus.ACTIVE_PAID,
                'notes': 'Pilote Mérifield : activation manuelle, sans encaissement. Limites provisoires.',
            })
            if created and is_default:
                Plan.objects.filter(user_type=user_type, is_default=True).exclude(pk=plan.pk).update(is_default=False)
                plan.is_default = True
                plan.save(update_fields=['is_default'])
            if public:
                Offer.objects.get_or_create(code=code, defaults={
                    'engine_plan_code': code, 'name': name, 'description': description,
                    'published': True, 'ordering': index * 10,
                })
        self.stdout.write(self.style.SUCCESS('Offres pilotes disponibles. Aucun tarif ni prélèvement automatique configuré.'))
