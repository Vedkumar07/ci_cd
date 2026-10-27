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
from report import baseline, explain, parse_codex_events
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
