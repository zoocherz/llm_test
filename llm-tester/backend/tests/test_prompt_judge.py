import unittest
from app.services.prompt_rendering import render_prompt, validate_prompt
from app.services.judge_evaluation import parse_judgment
from app.services.v1_providers import ProviderExecutionError


class PromptJudgeTests(unittest.TestCase):
    def test_independent_ranges(self):
        criteria = [{'key': 'accuracy', 'min_score': 0, 'max_score': 5}, {'key': 'style', 'min_score': -2, 'max_score': 2}]
        result = parse_judgment('{"scores":{"accuracy":5,"style":-1},"rationale":"ok"}', criteria, 0.7, 'independent')
        self.assertIsNone(result['score'])
        self.assertNotIn('passed', result)
        for text in ['{"scores":{"accuracy":6,"style":0},"rationale":"bad"}', '{"scores":{"accuracy":NaN,"style":0},"rationale":"bad"}']:
            with self.assertRaises(ProviderExecutionError):
                parse_judgment(text, criteria, 0.7, 'independent')

    def test_nested_fields_and_syntax_diagnostics(self):
        self.assertEqual(render_prompt('{{input.text}} / {{customer.name}}', {'text': 'hello', 'customer': {'name': 'Test'}}), 'hello / Test')
        self.assertEqual(render_prompt('{{input.text}} {{output}}', {'input': {'text': 'hello'}, 'output': 'answer'}), 'hello answer')
        with self.assertRaisesRegex(ValueError, 'строка 2, столбец 1'):
            validate_prompt('Instruction\n{{text | trim}}')
        with self.assertRaisesRegex(ValueError, 'Доступные поля input: text'):
            render_prompt('{{unknown}}', {'text': 'hidden value'})

    def test_literal_safe_substitution(self):
        self.assertEqual(render_prompt('A {{ text }} B {{number}}', {'text': '{{secret}}', 'number': 0}), 'A {{secret}} B 0')
        self.assertEqual(render_prompt('{{data}}', {'data': {'flag': True}}), '{"flag": true}')
        self.assertEqual(render_prompt('Return {"outer":{"x":1}} for {{text}}', {'text': 'a'}), 'Return {"outer":{"x":1}} for a')
        for template in ['{{missing}}', '{{a.b}}', '{{__import__("os")}}']:
            with self.assertRaises(ValueError):
                render_prompt(template, {})

    def test_judge_strict_scores(self):
        criteria = [{'key': 'a', 'weight': 0.25}, {'key': 'b', 'weight': 0.75}]
        result = parse_judgment('{"scores":{"a":0,"b":1},"rationale":"Reason"}', criteria, 0.7)
        self.assertEqual(result['score'], 0.75)
        self.assertTrue(result['passed'])
        for text in ['not json', '{"scores":{"a":0},"rationale":"x"}', '{"scores":{"a":true,"b":1},"rationale":"x"}', '{"scores":{"a":NaN,"b":1},"rationale":"x"}', '{"scores":{"a":0,"b":2},"rationale":"x"}']:
            with self.assertRaises(ProviderExecutionError):
                parse_judgment(text, criteria, 0.7)
