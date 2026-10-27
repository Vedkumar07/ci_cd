import io
import json
import os
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/poc'))
from report import explain, explain_gemini, fallback_report, NoRedirect


class GeminiTests(unittest.TestCase):
    def response(self, payload):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        return opener

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test-google-credential', 'GH_TOKEN': 'ci-private', 'POC_GEMINI_MODEL': ''})
    def test_text_request_has_no_tools_and_records_usage(self):
        opener = self.response({'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'Cause: assertion failed.'}]}}], 'usageMetadata': {'promptTokenCount': 12}})
        with patch('report.urllib.request.build_opener', return_value=opener):
            report, usage = explain_gemini('sanitized evidence')
        request = opener.open.call_args.args[0]
        self.assertTrue(request.full_url.startswith('https://generativelanguage.googleapis.com/'))
        self.assertNotIn('test-google-credential', request.full_url)
        self.assertNotIn('ci-private', str(request.headers))
        self.assertNotIn('tools', json.loads(request.data))
        self.assertEqual(opener.open.call_args.kwargs['timeout'], 180)
        self.assertIn('assertion failed', report)
        self.assertEqual(usage['usage']['promptTokenCount'], 12)
        self.assertEqual(usage['provider'], 'gemini')

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test-google-credential'})
    def test_rejects_incomplete_empty_and_tool_responses(self):
        for candidate in [
            {'finishReason': 'MAX_TOKENS', 'content': {'parts': [{'text': 'partial'}]}},
            {'finishReason': 'STOP', 'content': {'parts': []}},
            {'finishReason': 'STOP', 'content': {'parts': [{'functionCall': {'name': 'deploy'}}]}},
        ]:
            with self.subTest(candidate=candidate), patch('report.urllib.request.build_opener', return_value=self.response({'candidates': [candidate]})):
                with self.assertRaises(RuntimeError):
                    explain_gemini('evidence')

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test-google-credential'})
    def test_quota_error_redacts_key_and_preserves_evidence(self):
        error = urllib.error.HTTPError('https://generativelanguage.googleapis.com', 429, 'quota', {}, io.BytesIO(json.dumps({'error': {'message': 'quota exceeded test-google-credential'}}).encode()))
        with patch('report.urllib.request.build_opener') as build:
            build.return_value.open.side_effect = error
            with self.assertRaises(RuntimeError) as caught:
                explain_gemini('evidence')
        report, usage = fallback_report({'jobs': [{'name': 'test', 'log': 'AssertionError'}]}, caught.exception)
        self.assertNotIn('test-google-credential', report)
        self.assertIn('AssertionError', report)
        self.assertEqual(usage['ai_availability']['status'], 'quota')

    @patch.dict(os.environ, {'POC_AI_ENABLED': 'true', 'POC_AI_PROVIDER': 'gemini', 'POC_LOG_POLICY_APPROVED': 'true', 'GEMINI_API_KEY': ''})
    def test_missing_key_fails_before_render_or_network(self):
        with patch('report.subprocess.run') as render:
            with self.assertRaisesRegex(RuntimeError, 'GEMINI_API_KEY'):
                explain({'jobs': []})
            render.assert_not_called()

    def test_redirects_cannot_forward_key(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.org'))

    @patch.dict(os.environ, {'POC_AI_ENABLED': 'true', 'POC_AI_PROVIDER': 'gemini', 'POC_LOG_POLICY_APPROVED': 'true', 'GEMINI_API_KEY': 'test-google-credential', 'GH_TOKEN': 'private-ci-credential'})
    def test_shared_prompt_routes_to_gemini_without_codex(self):
        from report import ROOT
        first = ROOT / '_bmad/render/bmad-code-review/test/step-01-gather-context.md'
        with patch('report.subprocess.run', return_value=SimpleNamespace(stdout=f'Read `{first}`.')), patch('report.explain_gemini', return_value=('Explanation', {'provider': 'gemini'})) as gemini, patch('report.run_codex_process') as codex:
            report, usage = explain({'jobs': [{'name': 'test', 'log': 'AssertionError private-ci-credential'}]})
        codex.assert_not_called()
        prompt = gemini.call_args.args[0]
        self.assertIn('AssertionError', prompt)
        self.assertIn('docs/devops-context.md', prompt)
        self.assertNotIn('private-ci-credential', prompt)
        self.assertEqual(usage['provider'], 'gemini')


if __name__ == '__main__':
    unittest.main()
