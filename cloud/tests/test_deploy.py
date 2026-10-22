import importlib.util
from pathlib import Path
from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('configure', ROOT / 'deploy/configure.py')
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)


class DeployTests(SimpleTestCase):
    def test_secret_placeholders_are_replaced_and_existing_settings_preserved(self):
        values = dict(host='cloud.example.org', email='admin@example.org', endpoint='https://s3.example.org',
                      bucket='terrain', region='fr-par', access_key='abc', secret_key='secret$token', smtp_host='smtp.example.org',
                      smtp_user='mailer', smtp_password='pass$token', smtp_from='cloud@example.org')
        template = "DEBUG=1\nSECRET_KEY=change_me\nSALT_KEY=example\nSTORAGES='{\n\"old\": \"data\"\n}'\nUNCHANGED=keep\n"
        result = configure.build_environment(template, **values)
        self.assertNotIn('change_me', result)
        self.assertNotIn('"old"', result)
        self.assertIn('UNCHANGED=keep', result)
        self.assertIn("DEBUG='0'", result)
        self.assertIn('secret$token', result)
        with self.assertRaises(ValueError):
            configure.build_environment(template, **{**values, 'endpoint': 'http://insecure.example.org'})
