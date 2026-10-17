"""Archive old trace files and remove only this port's temporary probes; retain rollback APKs."""
import hashlib
import json
import shlex
from install_x9spro import ROOT, root
from device_actions import exclusive_ui


@exclusive_ui
def main():
    base = '/data/local/tmp/omnicam_muse_probe/'
    names = root('ls -1 ' + shlex.quote(base)).decode().splitlines()
    backups = [n for n in names if n.startswith(('embedded-', 'rollback-')) and n.endswith('.apk')]

    def sha(path):
        return root('sha256sum ' + shlex.quote(path)).decode().split()[0]

    backup_hashes = {n: sha(base + n) for n in backups}
    out = ROOT / 'evidence/experiments-20261017/final-trace-archive'
    out.mkdir(parents=True, exist_ok=True)
    traced = []
    for name in ['video-zoom-trace.jsonl', 'natural/debug-kernels.txt']:
        path = '/data/user/0/com.oplus.camera/files/jiege/' + name
        if root('test -f ' + shlex.quote(path) + ' && echo yes').strip() != b'yes':
            continue
        content = root('cat ' + shlex.quote(path))
        digest = hashlib.sha256(content).hexdigest()
        assert digest == sha(path)
        (out / name.replace('/', '-')).write_bytes(content)
        root('rm -f ' + shlex.quote(path))
        traced.append({'name': name, 'bytes': len(content), 'sha256': digest})
    flag = '/data/user/0/com.oplus.camera/files/jiege/debug-video-zoom'
    root('rm -f ' + shlex.quote(flag))
    removable = {'camera-sdk.sh', 'candidate.apk', 'characteristics.jar',
                 'experiment-settings.xml', 'final-README.md', 'final-customize.sh',
                 'final.apk', 'libdexkit.so', 'module.zip', 'multitouch.jar',
                 'muse-gr-init.apk', 'muse.apk', 'original-module-settings.xml',
                 'post-mount.sh', 'probe.jar', 'service.sh', 'symbols.json',
                 'touch-probe', 'upgrade-40002.zip', 'window.xml',
                 'xpan-animation-clean-ui.mp4', 'xpan-animation-stock-ui.mp4'}
    removed = sorted(removable.intersection(names))
    if removed:
        root('rm -f ' + ' '.join(shlex.quote(base + n) for n in removed))
    remaining = root('ls -1 ' + shlex.quote(base)).decode().splitlines()
    assert not removable.intersection(remaining)
    assert {n: sha(base + n) for n in backups} == backup_hashes
    report = {'archived_traces': traced, 'temporary_probe_files_removed': removed,
              'rollback_apks_preserved': backup_hashes, 'unknown_files_preserved': sorted(set(remaining) - set(backups))}
    (out.parent / 'probe-cleanup.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'traces_archived_and_removed': len(traced),
                      'temporary_files_removed': len(removed), 'rollback_apks_preserved': len(backups)}))


if __name__ == '__main__':
    main()
