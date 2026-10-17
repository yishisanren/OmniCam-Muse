"""Collect only reviewed experiments and final-version regressions; keep media private."""
import hashlib
import json
from pathlib import Path
from install_x9spro import ROOT


def main():
    out = ROOT / 'evidence/experiments-20261017'
    cases = [
        'master-blend0-real', 'master-blend50-real', 'master-blend100-real',
        'master-hncs-tele', 'master-hncs-wide', 'master-film-main',
        'soften0-reset-fixed', 'soften50-reset-fixed', 'soften100-reset-fixed',
        'gr-soften-isolation', 'highpixel-soften-isolation',
        'physical-hdf-weak-photo', 'physical-black-mist-medium-photo',
        'physical-white-mist-strong-photo', 'portra-physical-on', 'portra-physical-off',
        'xpan-developing-live', 'xpan-animation-clean', 'video-4k60-bw',
        'provideo-sdr-56x-video', 'provideo-olog2-2x-video',
        'master-grain86-standard', 'master-grain0-standard',
        'grain-clear-fixed-size100', 'grain-clear-fixed-size0',
    ]
    core = ['e2-normal', 'e2-gr-bw', 'e2-gr-positive', 'e2-pop',
            'e2-50mp', 'e2-200mp', 'e2-video4k60']
    package = json.loads((ROOT / 'evidence/package-verification.json').read_text())
    apk_sha = next(v['sha256'] for k, v in package.items() if k.endswith('.apk'))
    accepted = []
    for case in cases + core:
        record = json.loads((out / (case + '-media.json')).read_text())
        assert record['full_decode'] and record['stable_before_and_after_pull'], case
        assert not record.get('picture_stats', {}).get('zero_plane_green', False), case
        media = out / (case + Path(record['media']['_data']).suffix.lower())
        assert hashlib.sha256(media.read_bytes()).hexdigest() == record['sha256'], case
        if case in core or case.startswith('grain-clear-fixed-'):
            assert record['module_apk_sha256'] == apk_sha, case
        if case.startswith('grain-clear-fixed-'):
            state = record['native']['master-grain-status']
            assert 'last=1 amount=1' in state and 'grain type=2 ' in state, case
            assert ('size=1 ' if case.endswith('100') else 'size=0 ') in state, case
        if case.startswith('physical-'):
            expected = {'physical-hdf-weak-photo': 'HDF',
                        'physical-black-mist-medium-photo': 'black-mist',
                        'physical-white-mist-strong-photo': 'white-mist'}[case]
            state = record['native']['soft-light-status']
            assert 'filter=' + expected + ' ' in state and 'last=1 ' in state and 'result=1' in state, case
        if case in ['gr-soften-isolation', 'highpixel-soften-isolation']:
            assert 'changed=0 ' in record['native']['natural/status'], case
        accepted.append({k: record.get(k) for k in
                         ['case', 'size', 'sha256', 'module_apk_sha256', 'style', 'full_decode']})
    installed = json.loads((ROOT / 'evidence/device-20261017/acceptance/final-installed.json').read_text())
    boot = json.loads((ROOT / 'evidence/device-20261017/acceptance/camera-namespace.json').read_text())
    restored = json.loads((out / 'module-settings-restored.json').read_text())
    ui = json.loads((out / 'experiment-ui-restored.json').read_text())
    health = json.loads((out / 'final-experiment-health.json').read_text())
    assert installed['apk_sha256'] == apk_sha and not installed['mismatches']
    assert boot['marker_matches'] and boot['resource_hashes_match'] == 52
    assert restored['exact_original_bytes'] and ui['all_test_settings_restored']
    assert health['health'] == 'normal' and health['camera_symbols'] == 254 and health['gallery_symbols'] == 31
    for case, size in [('e2-50mp', [6144, 8160]), ('e2-200mp', [12288, 16320])]:
        assert json.loads((out / (case + '-media.json')).read_text())['size'] == size
    report = {'version': '4.0.0-x9spro.2', 'accepted_cases': accepted,
              'final_installation': installed, 'boot': boot,
              'module_settings': restored, 'ui_settings': ui, 'injection_health': health,
              'limits': ['No colour-chart or optical calibration',
                         'Not every look, lens and lighting condition was tested',
                         'ISZ sensor path verified; resolving power not quantified',
                         'Physical soft-light has no stock same-level optical A/B']}
    target = out / 'final-acceptance-summary.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'reviewed_experiments': len(cases), 'final_version_core_cases': len(core),
                      'settings_restored': True, 'report': str(target)}))


if __name__ == '__main__':
    main()
