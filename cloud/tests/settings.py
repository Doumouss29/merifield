from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
SECRET_KEY = 'local-tests-only-not-for-deployment'
DEBUG = True
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
ROOT_URLCONF = 'tests.urls'
INSTALLED_APPS = ['merifield_portal', 'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True,
    'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages', 'merifield_portal.context.branding']}}]
STATIC_URL = '/static/'
LOGIN_URL = '/accounts/login/'
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEFAULT_FROM_EMAIL = 'tests@example.invalid'
USE_TZ = True
LANGUAGE_CODE = 'fr'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
MERIFIELD_ENGINE = 'tests.fake_engine.FakeEngine'
MERIFIELD_PUBLIC_URL = 'https://cloud.example.invalid'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
