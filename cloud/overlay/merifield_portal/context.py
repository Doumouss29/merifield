from django.conf import settings


def branding(request):
    return {'brand': 'Mérifield Cloud', 'server_url': getattr(settings, 'MERIFIELD_PUBLIC_URL', ''),
            'engine_admin_uri': '/' + getattr(settings, 'QFIELDCLOUD_ADMIN_URI', 'admin/').lstrip('/')}
