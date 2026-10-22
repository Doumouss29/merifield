"""Non-production configuration for the disposable engine/PostGIS CI job."""
from pathlib import Path
from configure import build_environment
root = Path.cwd()
text = build_environment((root / '.env.example').read_text(),
    host='cloud.example.invalid', email='ci@example.invalid', endpoint='https://s3.example.invalid',
    bucket='merifield-ci', region='us-east-1', access_key='ci-only', secret_key='ci-only',
    smtp_host='smtp.example.invalid', smtp_user='ci-only', smtp_password='ci-only', smtp_from='ci@example.invalid')
text += "\nDJANGO_ALLOWED_HOSTS='cloud.example.invalid app testserver'\nEMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'\n"
(root / '.env').write_text(text)
(root / 'conf/ca').mkdir(parents=True, exist_ok=True)
