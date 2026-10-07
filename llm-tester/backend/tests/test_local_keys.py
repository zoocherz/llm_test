import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.core.config import Settings
from app.services.v1_providers import EnvironmentSecretResolver, ProviderConfigurationError


class LocalKeysTests(unittest.TestCase):
    def test_file_refresh_literal_values_precedence_and_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            with patch('app.services.v1_providers.ENV_FILE', path), patch.dict(os.environ, {}, clear=True), patch('app.services.v1_providers._read_windows_user_environment', return_value='user-value'):
                resolver = EnvironmentSecretResolver()
                path.write_text("TEST_KEY='literal#${HOME}'\n", encoding='utf-8-sig')
                self.assertEqual(resolver.resolve('env:TEST_KEY'), 'literal#${HOME}')
                os.environ['TEST_KEY'] = 'process-value'
                self.assertEqual(resolver.resolve('env:TEST_KEY'), 'process-value')
                del os.environ['TEST_KEY']
                path.write_text('TEST_KEY=updated\n', encoding='utf-8')
                self.assertEqual(resolver.resolve('env:TEST_KEY'), 'updated')
                path.write_text('TEST_KEY=\n', encoding='utf-8')
                self.assertEqual(resolver.resolve('env:TEST_KEY'), 'user-value')
                path.unlink()
                self.assertEqual(resolver.resolve('env:TEST_KEY'), 'user-value')
                self.assertNotIn('TEST_KEY', os.environ)

    def test_missing_and_unreadable_keys_fail_without_exposing_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            with patch('app.services.v1_providers.ENV_FILE', path), patch.dict(os.environ, {}, clear=True), patch('app.services.v1_providers._read_windows_user_environment', return_value=None):
                resolver = EnvironmentSecretResolver()
                self.assertFalse(resolver.is_available('env:TEST_KEY'))
                path.write_bytes(b'TEST_KEY=synthetic-private\xff')
                with self.assertRaises(ProviderConfigurationError) as caught:
                    resolver.resolve('env:TEST_KEY')
                self.assertNotIn('synthetic-private', str(caught.exception))
                self.assertFalse(resolver.is_available('env:TEST_KEY'))

    def test_provider_keys_do_not_break_or_enter_application_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('OPENAI_API_KEY=synthetic-private\nMAX_TEST_HISTORY=42\n', encoding='utf-8-sig')
            settings = Settings(_env_file=path)
            self.assertEqual(settings.MAX_TEST_HISTORY, 42)
            self.assertNotIn('synthetic-private', settings.model_dump_json())
