#!/usr/bin/env python3
"""Interactive first-install configuration. Secrets are never command arguments."""
import getpass
import json
import os
import re
import secrets
from pathlib import Path
from urllib.parse import urlsplit


def dotenv(value):
    value = str(value)
    if any(c in value for c in ['\n', '\r', "'"]):
        raise ValueError('Valeur non prise en charge : retour à la ligne ou apostrophe.')
    return "'" + value + "'"


def build_environment(template, *, host, email, endpoint, bucket, region, access_key, secret_key, smtp_host, smtp_user, smtp_password, smtp_from):
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]+\.[a-z]{2,}', host):
        raise ValueError('Saisir un nom de domaine public sans https:// ni chemin.')
    parsed = urlsplit(endpoint)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Le stockage doit disposer d’un endpoint HTTPS sans identifiants dans l’URL.')
    if not all([email, bucket, access_key, secret_key, smtp_host, smtp_user, smtp_password, smtp_from]):
        raise ValueError('Tous les paramètres sont nécessaires.')
    storages = {'default': {'BACKEND': 'qfieldcloud.filestorage.backend.QfcS3Boto3Storage', 'OPTIONS': {
        'access_key': access_key, 'secret_key': secret_key, 'bucket_name': bucket,
        'region_name': region, 'endpoint_url': endpoint.rstrip('/'),
    }}}
    replacements = {
        'DEBUG': '0', 'ENVIRONMENT': 'production', 'SECRET_KEY': secrets.token_urlsafe(72),
        'SALT_KEY': secrets.token_urlsafe(48), 'QFIELDCLOUD_HOST': host,
        'DJANGO_ALLOWED_HOSTS': host + ' app', 'DJANGO_SETTINGS_MODULE': 'merifield_settings',
        'DJANGO_USE_X_FORWARDED_HOST': '1',
        'POSTGRES_DB': 'merifield', 'POSTGRES_USER': 'merifield',
        'POSTGRES_PASSWORD': secrets.token_urlsafe(40), 'POSTGRES_HOST': 'db', 'POSTGRES_PORT': '5432',
        'POSTGRES_SSLMODE': 'disable',
        'COMPOSE_PROJECT_NAME': 'merifield',
        'COMPOSE_FILE': 'docker-compose.yml:merifield-deploy/compose.production.yml',
        'LETSENCRYPT_EMAIL': email, 'EMAIL_HOST': smtp_host, 'EMAIL_PORT': '587',
        'EMAIL_USE_TLS': '1', 'EMAIL_USE_SSL': '0', 'EMAIL_HOST_USER': smtp_user,
        'EMAIL_HOST_PASSWORD': smtp_password, 'DEFAULT_FROM_EMAIL': smtp_from,
        'ACCOUNT_EMAIL_VERIFICATION': 'mandatory', 'QFIELDCLOUD_DEFAULT_LANGUAGE': 'fr',
        'QFIELDCLOUD_DEFAULT_TIME_ZONE': 'Europe/Paris', 'SENTRY_DSN': '',
        'QFIELDCLOUD_WORKER_REPLICAS': '1', 'QFIELDCLOUD_WORKER_QFIELDCLOUD_URL': 'http://app:8000/api/v1/',
        'STORAGES': json.dumps(storages, ensure_ascii=False),
    }
    # Replace complete assignments, including multiline quoted JSON variables.
    pattern = re.compile(r"^([A-Z][A-Z0-9_]*)=(?:'[^']*'|\"[^\"]*\"|[^\n]*)", re.MULTILINE)
    seen = set()
    def replace(match):
        key = match.group(1)
        if key in replacements:
            seen.add(key)
            return key + '=' + dotenv(replacements[key])
        return match.group(0)
    result = pattern.sub(replace, template)
    result += '\n' + '\n'.join(key + '=' + dotenv(value) for key, value in replacements.items() if key not in seen) + '\n'
    return result


def main():
    root = Path.cwd()
    target = root / '.env'
    if target.exists():
        raise SystemExit('.env existe déjà. La configuration initiale ne l’écrasera pas.')
    values = dict(
        host=input('Domaine du cloud : ').strip().lower(),
        email=input('E-mail administrateur / certificat : ').strip(),
        endpoint=input('Endpoint S3 HTTPS : ').strip(),
        bucket=input('Bucket S3 existant : ').strip(),
        region=input('Région S3 : ').strip(),
        access_key=getpass.getpass('Clé d’accès S3 : '), secret_key=getpass.getpass('Clé secrète S3 : '),
        smtp_host=input('Serveur SMTP : ').strip(), smtp_user=input('Utilisateur SMTP : ').strip(),
        smtp_password=getpass.getpass('Mot de passe SMTP : '),
        smtp_from=input('Adresse e-mail expéditrice validée : ').strip(),
    )
    text = build_environment((root / '.env.example').read_text(), **values)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as output:
        output.write(text)
    (root / 'conf/ca').mkdir(parents=True, exist_ok=True)
    print('Configuration créée. Conserver .env hors de Git et dans une sauvegarde protégée.')


if __name__ == '__main__':
    main()
