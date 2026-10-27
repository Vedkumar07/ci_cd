import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/poc"))
from common import bounded, redact
from drift import provided_keys, required_keys
from report import baseline, explain, parse_codex_events, codex_error_detail, run_codex_process, fallback_report
from ci_api import API


class EvidenceTests(unittest.TestCase):
    def test_redacts_before_capping_and_keeps_401(self):
        with patch.dict(os.environ, {"EXAMPLE_TOKEN": "sensitive-credential"}):
            log = redact('401 Unauthorized password=hunter2 Authorization: Bearer abc123 https://u:pass@example.com sensitive-credential')
        for value in ['hunter2', 'abc123', 'u:pass', 'sensitive-credential']:
            self.assertNotIn(value, log)
        self.assertIn('401', log)
        self.assertLessEqual(len(bounded('x' * 10000, 100).encode()), 100)

    def test_private_key_and_json_secret(self):
        self.assertNotIn('keymaterial', redact('-----BEGIN RSA PRIVATE KEY-----\nkeymaterial\n-----END RSA PRIVATE KEY-----'))
        self.assertNotIn('abcd123', redact('{"db.password": "abcd123"}'))

    def test_java_defaults_and_bootstrap(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'Example.java').write_text('@Value("${billing.url}") String url;\n@Value("${optional:}") String optional;')
            (root/'bootstrap.yml').write_text('spring:\n  name: ${SERVICE_NAME}\n  optional: ${OTHER:default}\n')
            self.assertEqual(set(required_keys(root)), {'billing.url', 'SERVICE_NAME'})

    def test_rendered_config_payloads_and_empty_values(self):
        rendered = '''apiVersion: v1
kind: ConfigMap
data:
  DIRECT: ok
  EMPTY: ""
  UNRESOLVED: "${SECRET}"
  application.yml: |
    billing:
      url: https://example.com
  application.properties: |
    db.host=example
    db.empty=
'''
        self.assertEqual(provided_keys(rendered), {'DIRECT', 'billing.url', 'db.host'})

    def test_fixture_reports_are_honest_and_have_stage(self):
        evidence = {'jobs': [{'name': 'build', 'stage': 'build', 'log': '401 Unauthorized'}]}
        with patch.dict(os.environ, {'POC_AI_ENABLED': 'false'}):
            report, usage = explain(evidence)
        self.assertIn('authentication', report)
        self.assertIn('AI was not run', report)
        self.assertEqual(usage['tokens'], 0)
        self.assertIn('AI explanation unavailable', report)
        self.assertEqual(usage['ai_availability']['status'], 'disabled')

    def test_quota_fallback_preserves_pipeline_cause(self):
        evidence = {'jobs': [{'name': 'config', 'stage': 'verify', 'log': 'Config drift: BILLING_API_URL missing for staging'}]}
        report, usage = fallback_report(evidence, RuntimeError('Quota exceeded. Check your plan and billing details.'))
        self.assertIn('BILLING_API_URL', report)
        self.assertIn('AI explanation unavailable', report)
        self.assertIn('Quota exceeded', report)
        self.assertIn('credits and usage limits', report)
        self.assertNotIn('AI was not run', report)
        self.assertEqual(usage['mode'], 'fallback')
        self.assertEqual(usage['ai_availability']['status'], 'quota')
        self.assertIsNone(usage['tokens'])

    def test_fallback_reason_cannot_leak_key_or_escape_code_block(self):
        report, usage = fallback_report({'jobs': []}, RuntimeError('invalid api key sk-proj-demo-secret ```'))
        self.assertNotIn('sk-proj-demo-secret', report)
        self.assertNotIn('sk-proj-demo-secret', json.dumps(usage))
        self.assertEqual(report.count('```'), 2)

    def test_missing_key_fallback_has_setup_instruction(self):
        report, usage = fallback_report({'jobs': []}, RuntimeError('Set CODEX_API_KEY for Codex automation'))
        self.assertEqual(usage['ai_availability']['status'], 'missing_key')
        self.assertIn('OPENAI_API_KEY repository secret', report)

    def test_model_requires_log_policy_approval(self):
        with patch.dict(os.environ, {'POC_AI_ENABLED': 'true', 'POC_LOG_POLICY_APPROVED': 'false'}):
            with self.assertRaises(RuntimeError):
                explain({'jobs': []})

    def test_comment_updates_only_own_note(self):
        api = object.__new__(API)
        api.provider = 'github'
        with patch.dict(os.environ, {'POC_PR_NUMBER': '7'}), patch.object(api, 'pages', return_value=[{'id': 8, 'body': '<!-- poc2-failure-report -->', 'user': {'login': 'github-actions[bot]'}}]), patch.object(api, 'request') as request:
            api.post('new report')
            self.assertEqual(request.call_args.args[0:2], ('/issues/comments/8', 'PATCH'))

    def test_pagination_collects_multiple_pages(self):
        api = object.__new__(API)
        with patch.object(api, 'request', side_effect=[[{'id': i} for i in range(100)], [{'id': 101}]]):
            self.assertEqual(len(api.pages('/jobs')), 101)

    def test_does_not_overwrite_human_comment(self):
        api = object.__new__(API)
        api.provider = 'github'
        with patch.dict(os.environ, {'POC_PR_NUMBER': '7'}), patch.object(api, 'pages', return_value=[{'id': 8, 'body': '<!-- poc2-failure-report -->', 'user': {'login': 'human'}}]), patch.object(api, 'request') as request:
            api.post('new report')
            self.assertEqual(request.call_args.args[0:2], ('/issues/7/comments', 'POST'))

    def test_codex_has_no_ci_credentials_and_read_only_sandbox(self):
        from report import ROOT
        first = ROOT/'_bmad/render/bmad-code-review/test/step-01-gather-context.md'
        rendered = SimpleNamespace(stdout=f'Read fully and follow `{first}`.')
        answer = SimpleNamespace(stdout='\n'.join(json.dumps(e) for e in [{'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'Explanation'}}, {'type': 'turn.completed', 'usage': {'input_tokens': 7, 'output_tokens': 2}}]))
        with patch.dict(os.environ, {'POC_AI_ENABLED': 'true', 'POC_LOG_POLICY_APPROVED': 'true', 'GH_TOKEN': 'ci-credential', 'KUBECONFIG': '/secret', 'CODEX_API_KEY': 'ai-credential'}), patch('report.subprocess.run', return_value=rendered), patch('report.run_codex_process', return_value=answer.stdout) as run:
            report, usage = explain({'jobs': []})
        command = run.call_args.args[0]
        self.assertEqual(command[command.index('--sandbox')+1], 'read-only')
        self.assertIn('--ignore-user-config', command)
        self.assertIn('--ephemeral', command)
        self.assertIn('shell_tool', command)
        self.assertIn('apps', command)
        env = run.call_args.args[3]
        self.assertNotIn('GH_TOKEN', env)
        self.assertNotIn('KUBECONFIG', env)
        self.assertEqual(usage['usage']['input_tokens'], 7)
        self.assertIn('Explanation', report)

    def test_codex_rejects_incomplete_or_failed_turns(self):
        for event in [{'type': 'turn.failed'}, {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'partial'}}]:
            with self.assertRaises(RuntimeError):
                parse_codex_events(json.dumps(event))

    def test_codex_rejects_tool_activity(self):
        with self.assertRaises(RuntimeError):
            parse_codex_events(json.dumps({'type': 'item.started', 'item': {'type': 'command_execution', 'command': 'whoami'}}))

    def test_provider_error_is_visible_without_secret_or_prompt(self):
        events = '\n'.join(json.dumps(event) for event in [
            {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'PRIVATE PROMPT'}},
            {'type': 'turn.failed', 'error': {'message': '401 invalid key sk-proj-example-secret'}},
        ])
        detail = codex_error_detail(events, 'unrelated stderr')
        self.assertIn('401 invalid key', detail)
        self.assertNotIn('sk-proj-example-secret', detail)
        self.assertNotIn('PRIVATE PROMPT', detail)

    def test_startup_error_redacts_child_secret(self):
        detail = codex_error_detail('', 'Failed: child-credential', {'CODEX_API_KEY': 'child-credential'})
        self.assertIn('Failed:', detail)
        self.assertNotIn('child-credential', detail)

    def test_failed_process_preserves_provider_diagnostic(self):
        with patch('report.subprocess.Popen') as popen:
            process = popen.return_value.__enter__.return_value
            process.communicate.return_value = ('', 'Unknown argument: --example')
            process.returncode = 1
            with self.assertRaisesRegex(RuntimeError, 'Unknown argument: --example'):
                run_codex_process(['codex'], 'prompt', '/tmp', {'PATH': '/usr/bin'})

    def test_codex_missing_key_uses_actionable_error(self):
        with patch.dict(os.environ, {'POC_AI_ENABLED': 'true', 'POC_LOG_POLICY_APPROVED': 'true', 'CODEX_API_KEY': ''}):
            # Mock only workflow rendering, never make a model call.
            from report import ROOT
            first = ROOT/'_bmad/render/bmad-code-review/test/step-01-gather-context.md'
            with patch('report.subprocess.run', return_value=SimpleNamespace(stdout=f'Read `{first}`.')):
                with self.assertRaisesRegex(RuntimeError, 'CODEX_API_KEY'):
                    explain({'jobs': []})


if __name__ == '__main__':
    unittest.main()
