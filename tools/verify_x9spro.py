"""Differential invariants for the actual MTK stock snapshot and generated payload."""
import copy
import hashlib
import json
from pathlib import Path
from prepare_x9spro import ROOT, STOCK, read_json
from mtk_25mp import NODES, REMOVE


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def terms(node):
    result = []
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, list):
                result.append((key.rstrip('0123456789'), value))
            else:
                result.extend(terms(value))
    return result


def main():
    payload = ROOT / 'module/payload'
    profile = read_json(ROOT / 'module/profile.json')
    checked = []
    stock = read_json(STOCK / 'config/camera_unit_config')
    result = read_json(payload / 'camera_unit_config')
    for modes in result['mode_type_list'].values():
        modes[:] = [m for m in modes if m not in {'gr_mode', 'retro_camera_mode'}]
    for key in ['mode_operation_mode', 'capture_stream_number']:
        for mode in ['gr_mode', 'retro_camera_mode']:
            result[key].pop(mode, None)
    for key in ['gr_mode_case', 'gr_mode_hq_raw_case', 'retro_camera_case']:
        result['usecase_info'].pop(key, None)
    assert result == stock, 'Camera IDs, sensors, original use cases or MTK settings changed'
    checked.append('original camera IDs, sensor tuning and use cases preserved')

    stock_algo = read_json(STOCK / 'oplus_camera_algo_switch_config.decoded.json')
    result_algo = read_json(payload / 'oplus_camera_algo_switch_config')
    for group in ['aps_capture_configs', 'aps_preview_configs']:
        result_algo[group] = [x for x in result_algo[group] if x['mode'] not in {'grmode', 'retroCamera'}]
    # The only edits to existing capture rows are the enabled colour palette nodes.
    for before, after in zip(stock_algo['aps_capture_configs'], result_algo['aps_capture_configs']):
        for first, second in zip(before['entity'], after['entity']):
            if before['mode'] in ['common', 'portrait', 'aiHighPixel'] and first.get('enable') == 1:
                assert second.get('aps_algo_color_palette') == 1
                if 'aps_algo_color_palette' in first:
                    second['aps_algo_color_palette'] = first['aps_algo_color_palette']
                else:
                    second.pop('aps_algo_color_palette', None)
    assert stock_algo == result_algo, 'An original algorithm pipeline changed unexpectedly'
    checked.append('all original algorithm pipelines preserved apart from declared palette enablement')

    original = read_json(STOCK / 'oplus_camera_aps_config.decoded.json')
    base = read_json(payload / 'oplus_camera_aps_config')
    assert base['file_data'][:-1] == original['file_data']
    assert base['file_data'][-1]['VendorTag'] == 'com.oplus.color.palette.portrait.lut.weight'
    for key in original.keys() - {'file_data'}:
        assert base[key] == original[key]
    checked.append('base APS calibration, bit depth and thermal tables preserved')

    original = read_json(STOCK / 'oplus_camera_preview_decision_config.json.decoded.json')
    relaxed = read_json(payload / 'unlock25mp/oplus_camera_preview_decision_config.json')
    before = {x['mode']: x for x in original['multiAlgo']['algo']}
    after = {x['mode']: x for x in relaxed['multiAlgo']['algo']}
    assert before.keys() == after.keys()
    assert original['singleAlgo'] == relaxed['singleAlgo']
    assert sha(payload / 'oplus_camera_preview_decision_config.json') == sha(STOCK / 'config/oplus_camera_preview_decision_config.json')
    for name in before:
        if name not in NODES:
            assert before[name] == after[name], name
        else:
            old = terms(before[name]['condition'])
            expected = [t for t in old if t[1][0] not in REMOVE]
            assert sorted(map(str, terms(after[name]['condition']))) == sorted(map(str, expected))
            assert any(t[1][0] == 'aecDolState' for t in expected)
            assert any(t[1][0] == 'oplusMeta->com.qti.stats_control.is_flash_snapshot' for t in expected)
    assert 'isBigFaceScene' not in json.dumps(before['ALGO_HR_HQ_200M'])
    checked.append('only three normal-photo 25MP nodes relaxed; all 200MP conditions unchanged')

    assert not (ROOT / 'module/system/odm/lib64/libAlgoInterface.so').exists()
    assert sha(ROOT / 'module/system/odm/lib64/libBasicTonePhotoX9.so') == sha(STOCK / 'libBasicTonePhoto.so')
    assert not (payload / 'isp').exists() and not (payload / 'gamma').exists()
    assert (ROOT / 'app/src/main/assets/device_profile.json').read_bytes() == (ROOT / 'module/profile.json').read_bytes()
    checked.append('MTK original BasicTone backend and AlgoInterface retained; no Qualcomm ISP/gamma payload')
    report = {'checks': checked, 'profile_sha256': sha(ROOT / 'module/profile.json'), 'runtime_acceptance': 'pending'}
    (ROOT / 'evidence/config-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
