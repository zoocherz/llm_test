import unittest
from app.services.prompt_import import import_prompt_yaml


class PromptImportTests(unittest.TestCase):
    def test_crt_text_is_combined_without_importing_service_settings(self):
        result = import_prompt_yaml(b'name: imported\nprompt: first\ninstructions: second\nmodel: ignored\nnotification: null\n')
        self.assertEqual(result['template'], 'first\n\nsecond')
        self.assertEqual(result['ignored_fields'], ['model', 'notification'])
        self.assertNotIn('ignored', result['template'])

    def test_unsafe_ambiguous_and_oversize_yaml_is_rejected(self):
        for content in [b'!!python/object/apply:os.system [echo unsafe]', b'prompt: &a text\ninstructions: *a', b'prompt: a\nprompt: b', b'template: a\nprompt: b', b'- text', b'x' * (256 * 1024 + 1)]:
            with self.assertRaises(ValueError):
                import_prompt_yaml(content)
