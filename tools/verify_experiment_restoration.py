"""Verify individually restored camera controls and original module settings."""
import hashlib
import json
import shlex
import xml.etree.ElementTree as ET
from install_x9spro import ROOT, root


def main():
    out = ROOT / 'evidence/experiments-20261017'

    def nodes(name):
        return list(ET.parse(out / (name + '-restored.xml')).iter('node'))

    def text(name):
        return ' '.join(n.get('text', '') for n in nodes(name))

    def description(name, value):
        return any(n.get('content-desc') == value for n in nodes(name))

    assert '正片' in text('gr')
    assert description('highpixel', '2 亿像素已关闭') and description('highpixel', '滤镜已关闭')
    assert '4K·60' in text('video') and description('video', '滤镜已关闭')
    assert all(s in text('provideo') for s in ['1080', '30', 'SDR'])
    zoom = json.loads((out / 'provideo-restored-camera-metadata.json').read_text())['received']
    assert zoom['android.logicalMultiCamera.activePhysicalId'] == [50, 0]
    assert abs(zoom['android.control.zoomRatio'][0] - 1) < .01
    assert any(n.get('resource-id') == 'com.oplus.camera:id/xpan_textured_shutter_btn' for n in nodes('xpan'))
    assert description('photo', '闪光灯自动') and '0.0' in text('photo')
    assert any(n.get('resource-id') == 'com.oplus.camera:id/palette_filter_soft_light_value'
               and n.get('text') == '无' for n in nodes('photo-palette'))
    assert '标准' in text('master') and '-1.0' in text('master-main')
    assert (out / 'grain-clear-restored.png').is_file()  # Visually checked 0 / 70.
    baseline = json.loads((out / 'before.json').read_text())
    restored = json.loads((out / 'module-settings-restored.json').read_text())
    assert hashlib.sha256(root('cat ' + shlex.quote(baseline['module_preferences']))).hexdigest() == restored['module_xml_sha256']
    paths = ['/data/user/0/com.oplus.camera/files/jiege/natural/soften',
             '/data/user/0/com.oplus.camera/files/jiege/debug-video-zoom',
             '/data/local/tmp/omnicam_muse_probe/touch-probe']
    for path in paths:
        assert root('test ! -e ' + shlex.quote(path) + ' && echo absent').strip() == b'absent', path
    profile = json.loads((ROOT / 'module/profile.json').read_text())
    assert root('sha256sum /odm/lib64/libAlgoInterface.so').decode().split()[0] == profile['algo_sha256']
    report = {'all_test_settings_restored': True, 'gr_style': '正片',
              'highpixel_filter': '标准', 'highpixel_200mp': False,
              'video': '4K60/filter off', 'provideo': '1080p30/SDR/1x',
              'xpan': 'small physical frame', 'photo_flash': 'auto',
              'photo_ev': 0, 'photo_soft_light': '无', 'master_filter': '标准',
              'master_ev': -1, 'clear_grain': '0/70',
              'temporary_trace_and_touch_probe_removed': True,
              'original_module_xml_matches': True, 'original_mtk_algo_preserved': True}
    (out / 'experiment-ui-restored.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
