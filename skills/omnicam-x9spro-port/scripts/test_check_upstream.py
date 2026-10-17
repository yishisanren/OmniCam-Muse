"""Behavioral checks: updates, prereleases, failures and immutable accepted state."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from check_upstream import evaluate, release_fingerprint, run, write_report

BASE = {'schema_version': 1, 'upstream_repository': 'owner/source', 'upstream_branch': 'main',
        'accepted_upstream_commit': 'a' * 40, 'accepted_upstream_release': None,
        'accepted_port_version': '4.0.0-x9spro.2'}


class UpstreamCheckTest(unittest.TestCase):
    def test_unchanged_and_commit_update(self):
        self.assertFalse(evaluate(BASE, 'a' * 40, None)['needs_adaptation'])
        result = evaluate(BASE, 'b' * 40, None)
        self.assertTrue(result['source_changed'])
        self.assertEqual(result['status'], 'update_available')

    def test_prerelease_and_asset_replacement(self):
        source = {'id': 1, 'tag_name': 'next', 'prerelease': True, 'draft': False,
                  'published_at': '2026-10-17T00:00:00Z', 'updated_at': '2026-10-17T00:00:00Z',
                  'html_url': 'https://github.com/owner/source/releases/tag/next',
                  'assets': [{'id': 10, 'name': 'module.zip', 'size': 100}]}
        release = release_fingerprint([source])
        self.assertTrue(evaluate(BASE, 'a' * 40, release)['release_changed'])
        accepted = {**BASE, 'accepted_upstream_release': release}
        self.assertFalse(evaluate(accepted, 'a' * 40, release)['needs_adaptation'])
        changed = copy.deepcopy(source)
        changed['assets'][0]['id'] = 11
        self.assertTrue(evaluate(accepted, 'a' * 40, release_fingerprint([changed]))['release_changed'])
        source['draft'] = True
        self.assertIsNone(release_fingerprint([source]))

    def test_invalid_commit_is_not_no_update(self):
        with self.assertRaises(ValueError):
            evaluate(BASE, 'not-a-commit', None)

    def test_failure_preserves_checkpoint_and_overwrites_stale_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            checkpoint = root / 'maintenance/upstream.json'
            checkpoint.parent.mkdir()
            checkpoint.write_text(json.dumps(BASE))
            before = checkpoint.read_bytes()
            def fail(_):
                raise HTTPError('https://api.github.com/example', 403, 'rate limited', {}, None)
            result, code = run(root, fetch=fail)
            self.assertEqual(code, 2)
            self.assertEqual(result['status'], 'error')
            output = root / 'evidence/check.json'
            write_report(output, root, {'status': 'up_to_date'})
            write_report(output, root, result)
            self.assertEqual(json.loads(output.read_text())['status'], 'error')
            self.assertEqual(before, checkpoint.read_bytes())
            with self.assertRaises(ValueError):
                write_report(checkpoint, root, result)

    def test_success_does_not_accept_new_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'maintenance/upstream.json'
            path.parent.mkdir()
            path.write_text(json.dumps(BASE))
            before = path.read_bytes()
            def fetch(route):
                return [] if '/releases?' in route else {'object': {'sha': 'b' * 40}}
            report, code = run(root, fetch=fetch)
            self.assertEqual(code, 0)
            self.assertTrue(report['needs_adaptation'])
            self.assertEqual(before, path.read_bytes())


if __name__ == '__main__':
    unittest.main()
