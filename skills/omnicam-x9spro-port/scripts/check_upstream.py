#!/usr/bin/env python3
"""Read public upstream state; never modify the accepted baseline or a phone."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen


def fetch_json(route):
    request = Request('https://api.github.com/' + route,
                      headers={'Accept': 'application/vnd.github+json',
                               'User-Agent': 'OmniCam-X9sPro-Upstream-Check'})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def release_fingerprint(releases):
    if not isinstance(releases, list):
        raise ValueError('Invalid releases response')
    public = [r for r in releases if not r.get('draft') and r.get('published_at')]
    if not public:
        return None
    release = max(public, key=lambda r: r['published_at'])
    return {
        'id': release['id'], 'tag_name': release['tag_name'],
        'prerelease': bool(release.get('prerelease')),
        'published_at': release['published_at'], 'updated_at': release['updated_at'],
        'html_url': release['html_url'],
        'assets': sorted([
            {key: asset.get(key) for key in ['id', 'name', 'size', 'digest', 'updated_at']}
            for asset in release.get('assets', [])
        ], key=lambda a: (a['name'] or '', a['id'] or 0)),
    }


def evaluate(baseline, head, release):
    if baseline.get('schema_version') != 1:
        raise ValueError('Unsupported baseline schema')
    accepted = baseline['accepted_upstream_commit']
    if not isinstance(head, str) or not re.fullmatch(r'[0-9a-f]{40}', head):
        raise ValueError('Invalid upstream commit')
    if not isinstance(accepted, str) or not re.fullmatch(r'[0-9a-f]{40}', accepted):
        raise ValueError('Invalid accepted commit')
    source_changed = head != accepted
    release_changed = release != baseline['accepted_upstream_release']
    changed = source_changed or release_changed
    return {'status': 'update_available' if changed else 'up_to_date',
            'needs_adaptation': changed, 'source_changed': source_changed,
            'release_changed': release_changed, 'accepted_commit': accepted,
            'head_commit': head, 'release': release,
            'accepted_port_version': baseline['accepted_port_version']}


def check(workspace, fetch=fetch_json):
    path = workspace / 'maintenance/upstream.json'
    baseline = json.loads(path.read_text())
    repository, branch = baseline['upstream_repository'], baseline['upstream_branch']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid upstream repository')
    if not isinstance(branch, str) or not branch or any(c in branch for c in '\r\n\x00'):
        raise ValueError('Invalid upstream branch')
    prefix = 'repos/' + repository
    head = fetch(prefix + '/git/ref/heads/' + quote(branch, safe=''))['object']['sha']
    releases = fetch(prefix + '/releases?per_page=100')
    result = evaluate(baseline, head, release_fingerprint(releases))
    return {'upstream_repository': repository, 'upstream_branch': branch, **result}


def run(workspace, fetch=fetch_json):
    stamp = datetime.now(timezone.utc).isoformat()
    try:
        return {'checked_at_utc': stamp, **check(workspace, fetch)}, 0
    except Exception as error:
        # A failed check must not be interpreted as "no update" or reuse a
        # previous green result. No tokens are used or included in this tool.
        return {'checked_at_utc': stamp, 'status': 'error',
                'error': type(error).__name__ + ': ' + str(error)}, 2


def write_report(path, workspace, report):
    if not path.resolve().is_relative_to((workspace / 'evidence').resolve()):
        raise ValueError('Check output must be inside the workspace evidence directory')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    report, code = run(workspace)
    if args.output:
        output = args.output if args.output.is_absolute() else workspace / args.output
        try:
            write_report(output, workspace, report)
        except (OSError, ValueError) as error:
            report = {'status': 'error', 'error': type(error).__name__ + ': ' + str(error)}
            code = 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    sys.exit(main())
