"""Production overlay loaded by both app and worker_wrapper containers."""
import os
from pathlib import Path
from qfieldcloud.settings import *  # noqa: F403 -- extend the pinned engine

PORTAL_ROOT = Path(__file__).parent / 'merifield_portal'
INSTALLED_APPS = ['merifield_portal.apps.MerifieldPortalConfig'] + INSTALLED_APPS
ROOT_URLCONF = 'merifield_urls'
TEMPLATES[0]['DIRS'].insert(0, str(PORTAL_ROOT / 'templates'))
TEMPLATES[0]['OPTIONS']['context_processors'].append('merifield_portal.context.branding')
WHITELABEL = {'site_title': 'Mérifield Cloud', 'logo_navbar': 'merifield/logo.svg',
              'logo_main': 'merifield/logo.svg', 'favicon': 'merifield/logo.svg', 'logo_alt': 'Mérifield Cloud'}
LANGUAGE_CODE = 'fr'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/login/'
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[Mérifield Cloud] '
MERIFIELD_PUBLIC_URL = 'https://' + os.environ['QFIELDCLOUD_HOST']

# Defaults for an HTTPS deployment; trusted proxy is the bundled nginx.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = [MERIFIELD_PUBLIC_URL]

JAZZMIN_SETTINGS = {**globals().get('JAZZMIN_SETTINGS', {}),
    'site_title': 'Mérifield Cloud', 'site_header': 'Mérifield Cloud',
    'site_brand': 'Mérifield Cloud', 'site_logo': 'merifield/logo.svg',
    'site_icon': 'merifield/logo.svg', 'login_logo': 'merifield/logo.svg',
    'welcome_sign': 'Administration Mérifield Cloud', 'copyright': 'Mérifield',
}

SPECTACULAR_SETTINGS = {**globals().get('SPECTACULAR_SETTINGS', {}), 'TITLE': 'Mérifield Cloud API'}
