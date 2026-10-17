"""Generate PME110 overlays by merging narrow additions into its own firmware.

The input snapshots are private and intentionally excluded from Git. No camera
IDs, calibration, MTK vendor flags or pre-existing capture pipelines are copied
from PMA110. Requires the upstream resource tree and decoded original configs.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
from config_codec import decode
from mtk_25mp import patch as patch_25mp
from export_x9spro_scene import main as export_scene

ROOT = Path(__file__).resolve().parent.parent
CAPTURE = Path(os.environ.get('MUSE_CAPTURE_DIR', ROOT / 'evidence/device-20261017'))
STOCK = CAPTURE / 'stock'
DONOR = ROOT / 'evidence/upstream-module'
MODULE = ROOT / 'module'


def read_json(path):
    # Android's JSON parser permits comments and literal newlines in strings.
    text = path.read_text()
    text = re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/',
                  lambda m: m[0] if m[0].startswith('"') else '', text)
    return json.loads(text, strict=False)


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def varint(data, pos):
    value = shift = 0
    while True:
        byte = data[pos]
        pos += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, pos
        shift += 7
        if shift > 63:
            raise ValueError('invalid varint')


def encode_varint(value):
    data = bytearray()
    while value > 127:
        data.append((value & 127) | 128)
        value >>= 7
    data.append(value)
    return bytes(data)


def parse_wire(data):
    fields = []
    pos = 0
    while pos < len(data):
        tag, pos = varint(data, pos)
        wire = tag & 7
        if wire == 2:
            size, pos = varint(data, pos)
            value = data[pos:pos + size]
            if len(value) != size:
                raise ValueError('truncated protobuf')
            pos += size
        elif wire == 0:
            value, pos = varint(data, pos)
        else:
            raise ValueError(f'unsupported protobuf wire {wire}')
        fields.append((tag >> 3, wire, value))
    return fields


def encode_wire(fields):
    return b''.join(encode_varint((field << 3) | wire) +
                    (encode_varint(len(value)) + value if wire == 2 else encode_varint(value))
                    for field, wire, value in fields)


def feature_overlay():
    original = parse_wire((STOCK / 'config/camera_unit_feature_config.protobuf').read_bytes())
    donor = parse_wire((DONOR / 'payload/camera_unit_feature_config.protobuf').read_bytes())
    pool = [v for n, w, v in original if n == 1]
    donor_pool = [v for n, w, v in donor if n == 1]
    extra = []

    def remap(index):
        value = donor_pool[index]
        if value not in pool:
            pool.append(value)
            extra.append((1, 2, value))
        return pool.index(value)

    def conflict_list(data):
        return encode_wire([(n, w, encode_wire([(f, wire, remap(v))
                             for f, wire, v in parse_wire(item)]))
                            for n, w, item in parse_wire(data)])

    def feature(data):
        out = []
        for n, w, value in parse_wire(data):
            if 1 <= n <= 6:
                value = remap(value)
            elif n == 8:
                value = encode_wire([(f, wire, remap(v) if f == 1 else conflict_list(v))
                                     for f, wire, v in parse_wire(value)])
            out.append((n, w, value))
        return encode_wire(out)

    def mode_table(data):
        out = []
        for n, w, item in parse_wire(data):
            pair = parse_wire(item)
            camera_index = next(v for f, wire, v in pair if f == 1)
            if donor_pool[camera_index] == b'rear_ultra_tele':
                continue
            mapped = []
            for f, wire, value in pair:
                value = remap(value) if f == 1 else encode_wire(
                    [(ff, ww, feature(vv)) for ff, ww, vv in parse_wire(value)])
                mapped.append((f, wire, value))
            out.append((n, w, encode_wire(mapped)))
        return encode_wire(out)

    additions = []
    donor_highpixel = {}
    for n, w, data in donor:
        if n != 2:
            continue
        for f, wire, entry in parse_wire(data):
            fields = parse_wire(entry)
            name = next(v for ff, ww, v in fields if ff == 1)
            if name == b'high_pixel_mode':
                cameras = next(v for ff, ww, v in fields if ff == 2)
                for _, _, camera in parse_wire(cameras):
                    values = dict((ff, v) for ff, ww, v in parse_wire(camera))
                    donor_highpixel[donor_pool[values[1]]] = parse_wire(values[2])
            if name in [b'gr_mode', b'retro_camera_mode']:
                additions.append((f, wire, encode_wire(
                    [(ff, ww, v if ff == 1 else mode_table(v)) for ff, ww, v in fields])))
    result = []
    for n, w, value in original:
        if n == 2:
            entries = []
            for field, wire, entry in parse_wire(value):
                mode = parse_wire(entry)
                if next(v for f, ww, v in mode if f == 1) == b'high_pixel_mode':
                    cameras = []
                    for cf, cw, camera in parse_wire(next(v for f, ww, v in mode if f == 2)):
                        parts = parse_wire(camera)
                        camera_name = pool[next(v for f, ww, v in parts if f == 1)]
                        features = parse_wire(next(v for f, ww, v in parts if f == 2))
                        if camera_name in {b'front_main', b'rear_main', b'rear_wide', b'rear_tele'}:
                            existing = {tuple(v for f, ww, v in parse_wire(data) if f in [1, 2]) for _, _, data in features}
                            for ff, fw, data in donor_highpixel[camera_name]:
                                values = dict((f, v) for f, ww, v in parse_wire(data))
                                if donor_pool[values[1]] not in {b'com.oplus.camera.feature.filter', b'com.oplus.camera.feature.beauty'}:
                                    continue
                                mapped = feature(data)
                                identity = tuple(v for f, ww, v in parse_wire(mapped) if f in [1, 2])
                                if identity not in existing:
                                    features.append((ff, fw, mapped))
                                    existing.add(identity)
                        cameras.append((cf, cw, encode_wire([(f, ww, encode_wire(features) if f == 2 else v) for f, ww, v in parts])))
                    mode = [(f, ww, encode_wire(cameras) if f == 2 else v) for f, ww, v in mode]
                    entry = encode_wire(mode)
                entries.append((field, wire, entry))
            value = encode_wire(entries + additions)
        result.append((n, w, value))
    # String indices reference the concatenation of all repeated field-1 values.
    result += extra
    (MODULE / 'payload/camera_unit_feature_config.protobuf').write_bytes(encode_wire(result))


def prepare_inputs():
    live = json.loads((CAPTURE / 'live-profile.json').read_text())
    assert live['model'] == 'PME110' and live['firmware'] == 'PME110_17.0.0.103(CN01)'
    assert live['com.oplus.camera'] == '7.006.121'
    odm = CAPTURE / 'stock-tree/odm'
    (STOCK / 'config').mkdir(parents=True, exist_ok=True)
    for path in (odm / 'etc/camera/config').iterdir():
        shutil.copy2(path, STOCK / 'config' / path.name)
    for name in ['libAlgoInterface.so', 'libBasicTonePhoto.so', 'libOplusSecurity.so']:
        shutil.copy2(odm / 'lib64' / name, STOCK / name)
    security = STOCK / 'libOplusSecurity.so'
    for name in ['oplus_camera_config', 'oplus_camera_algo_switch_config', 'oplus_camera_aps_config',
                 'oplus_camera_preview_decision_config.json']:
        data = decode(STOCK / 'config' / name, security)
        (STOCK / (name + '.decoded.json')).write_bytes(data)
        read_json(STOCK / (name + '.decoded.json'))
    camera_apk = 'OplusCamera-7.006.121.apk'
    shutil.copy2(CAPTURE / camera_apk, STOCK / camera_apk)
    assert hashlib.sha256((STOCK / camera_apk).read_bytes()).hexdigest() == '6ff0a021288529bdd8eb957827322c71b85c50c93b1715f9e34ab77a7c70a0e6'
    assert hashlib.sha256((STOCK / 'libAlgoInterface.so').read_bytes()).hexdigest() == '8e6ce18cefae51089b8318970daea3087fb6434fed42d55810bf7456df8d66e5'
    write_json(STOCK / 'device-profile.json', dict(model=live['model'], firmware=live['firmware'],
               camera=live['com.oplus.camera'], camera_apk=camera_apk))
    (DONOR / 'payload').mkdir(parents=True, exist_ok=True)
    for name in ['camera_unit_feature_config.protobuf', 'oplus_camera_config']:
        data = subprocess.check_output(['git', 'show', '8f373e10b17c95532a3ff2f41c4777ca797da947:module/payload/' + name], cwd=ROOT)
        (DONOR / 'payload' / name).write_bytes(data)


def main():
    prepare_inputs()
    export_scene()
    device = read_json(STOCK / 'device-profile.json')
    assert device['model'] == 'PME110', 'Only the inspected MTK device is supported'
    unit = read_json(STOCK / 'config/camera_unit_config')
    original_unit = copy.deepcopy(unit)
    for camera, modes in unit['mode_type_list'].items():
        for new, base in [('gr_mode', 'professional_mode'), ('retro_camera_mode', 'photo_mode')]:
            if base in modes and new not in modes:
                modes.append(new)
    for new, base in [('gr_mode', 'professional_mode'), ('retro_camera_mode', 'photo_mode')]:
        unit['mode_operation_mode'][new] = unit['mode_operation_mode'][base]
        if base in unit['capture_stream_number']:
            unit['capture_stream_number'][new] = copy.deepcopy(unit['capture_stream_number'][base])
    for new, base in [('gr_mode_case', 'professional_case'), ('gr_mode_hq_raw_case', 'professional_hqraw_case'),
                      ('retro_camera_case', 'sat_photo_case')]:
        unit['usecase_info'][new] = copy.deepcopy(unit['usecase_info'][base])
    write_json(MODULE / 'payload/camera_unit_config', unit)
    feature_overlay()

    config = read_json(STOCK / 'oplus_camera_config.decoded.json')
    donor_config = read_json(DONOR / 'payload/oplus_camera_config')
    rows = {row['VendorTag']: row for row in config}
    allow = {
        'com.oplus.gr.mode.support', 'com.oplus.available.gr.mode.zoomvalues',
        'com.oplus.gr.mode.marked.zoomvalues', 'com.oplus.camera.gr.raw.capture_defer.not.support',
        'com.oplus.feature.retro.camera.support', 'com.oplus.feature.retro.camera.livephoto.output.size',
        'com.oplus.camera.retro.fisheye.enable', 'com.oplus.feature.color.palette.support',
        'com.oplus.ipu.color.palette.texture.support', 'com.oplus.feature.tilt.shift.photo.support',
    }
    changes = []
    for row in donor_config:
        key = row['VendorTag']
        if key not in allow:
            continue
        row = copy.deepcopy(row)
        if key == 'com.oplus.available.gr.mode.zoomvalues':
            row['Value'] = rows['com.oplus.pro.zoom.marked.zoomvalues']['Value']
            row['Count'] = str(len(row['Value'].split(',')))
        if key in rows:
            rows[key].update(row)
        else:
            config.append(row)
            rows[key] = row
        changes.append(key)
    flash = {'VendorTag': 'com.oplus.flashlevel.configurable.support', 'Type': 'Byte', 'Count': '1', 'Value': '1'}
    if flash['VendorTag'] in rows:
        rows[flash['VendorTag']].update(flash)
    else:
        config.append(flash)
    changes.append(flash['VendorTag'])
    version = rows['com.oplus.camera.mode.data.db.version']
    version['Value'] = str(int(version['Value']) + 1)
    changes.append(version['VendorTag'])
    write_json(MODULE / 'payload/oplus_camera_config', config)

    algo = read_json(STOCK / 'oplus_camera_algo_switch_config.decoded.json')
    original_algo = copy.deepcopy(algo)
    for groups in ['aps_capture_configs', 'aps_preview_configs']:
        index = {group['mode']: group for group in algo[groups]}
        for new, base in [('retroCamera', 'common'), ('grmode', 'master')]:
            group = copy.deepcopy(index[base])
            group['mode'] = new
            algo[groups].append(group)
        if groups == 'aps_capture_configs':
            for group in algo[groups]:
                if group['mode'] in ['common', 'portrait', 'aiHighPixel']:
                    for entity in group['entity']:
                        if entity.get('enable') == 1:
                            entity['aps_algo_color_palette'] = 1
    write_json(MODULE / 'payload/oplus_camera_algo_switch_config', algo)

    aps = read_json(STOCK / 'oplus_camera_aps_config.decoded.json')
    # Keep all sensor, bit-depth and ISP parameters, including MTK's 8-bit BasicTone setting.
    aps['file_data'].append({'VendorTag': 'com.oplus.color.palette.portrait.lut.weight',
                             'Type': 'Float', 'Count': '1', 'Value': '0.85'})
    write_json(MODULE / 'payload/oplus_camera_aps_config', aps)

    # Keep the original MTK decision tree for every mode except the optional normal-photo 25MP copy.
    decision = read_json(STOCK / 'oplus_camera_preview_decision_config.json.decoded.json')
    (MODULE / 'payload/oplus_camera_preview_decision_config.json').write_bytes(
        (STOCK / 'config/oplus_camera_preview_decision_config.json').read_bytes())
    shutil.rmtree(MODULE / 'payload/unlock25mp', ignore_errors=True)
    shutil.rmtree(MODULE / 'payload/face200m', ignore_errors=True)
    unlock = MODULE / 'payload/unlock25mp'
    unlock.mkdir()
    write_json(unlock / 'oplus_camera_preview_decision_config.json', patch_25mp(decision))
    relaxed_aps = copy.deepcopy(aps)
    changed_thermal = set()
    for row in relaxed_aps['file_data']:
        if row['VendorTag'] in {'com.oplus.aps.params.qbc.thermallevel', 'com.oplus.aps.params.turboraw.thermallevel'}:
            values = row['Value'].split(',')
            assert len(values) == 21
            value = '1000' if '.qbc.' in row['VendorTag'] else '24'
            row['Value'] = ', '.join([value] * len(values))
            changed_thermal.add(row['VendorTag'])
    assert len(changed_thermal) == 2
    write_json(unlock / 'oplus_camera_aps_config', relaxed_aps)
    # This device has one original 200MP node and it already has no face condition.
    pixel = [x for x in decision['multiAlgo']['algo'] if x['mode'] == 'ALGO_HR_HQ_200M']
    assert len(pixel) == 1 and 'isBigFaceScene' not in json.dumps(pixel)
    (MODULE / 'payload/face200m').mkdir()
    write_json(MODULE / 'payload/face200m/not-required.json', {'reason': 'PME110 stock 200MP has no face gate'})


    for path in ['payload/isp', 'payload/gamma']:
        shutil.rmtree(MODULE / path, ignore_errors=True)
    (MODULE / 'system/odm/lib64/libAlgoInterface.so').unlink(missing_ok=True)
    # The router's X9 backend is THIS device's original BasicTone, not the Qualcomm donor.
    shutil.copy2(STOCK / 'libBasicTonePhoto.so', MODULE / 'system/odm/lib64/libBasicTonePhotoX9.so')
    report = {
        'version': next(line.split('=', 1)[1] for line in (MODULE / 'module.prop').read_text().splitlines() if line.startswith('version=')),
        'model': device['model'], 'firmware': device['firmware'], 'camera': device['camera'],
        'apk_sha256': hashlib.sha256((STOCK / device['camera_apk']).read_bytes()).hexdigest(),
        'algo_sha256': hashlib.sha256((STOCK / 'libAlgoInterface.so').read_bytes()).hexdigest(),
        'basictone_sha256': hashlib.sha256((STOCK / 'libBasicTonePhoto.so').read_bytes()).hexdigest(),
        'changed_config_keys': changes,
        'gr_zoom': rows['com.oplus.available.gr.mode.zoomvalues']['Value'],
        'untouched': ['camera IDs', 'device_info', 'MTK vendor tags', 'all original use cases',
                      'all original protobuf modes', 'all original gamma and ISP files', 'libAlgoInterface.so'],
        'not_enabled': ['Qualcomm ISP replacements', 'Qualcomm audio policy replacement', '200MP face unlock (stock already has no gate)'],
        'upstream_commit': '8f373e10b17c95532a3ff2f41c4777ca797da947',
        'features': {'unlock25mp': True, 'face200m_unlock': False, 'native_200mp': True},
    }
    report['mounted_files'] = {
        '/odm/etc/camera/config/' + name: hashlib.sha256((MODULE / 'payload' / name).read_bytes()).hexdigest()
        for name in ['camera_unit_config', 'camera_unit_feature_config.protobuf', 'oplus_camera_config',
                     'oplus_camera_algo_switch_config', 'oplus_camera_aps_config']
    }
    for library in sorted((MODULE / 'system/odm/lib64').glob('*.so')):
        report['mounted_files']['/odm/lib64/' + library.name] = hashlib.sha256(library.read_bytes()).hexdigest()
    report['mounted_files']['/odm/lib64/libAlgoInterface.so'] = report['algo_sha256']
    for lut in sorted((MODULE / 'payload/meishe_lut').iterdir()):
        if lut.is_file():
            report['mounted_files']['/odm/etc/camera/meishe_lut/' + lut.name] = hashlib.sha256(lut.read_bytes()).hexdigest()
    write_json(MODULE / 'profile.json', report)
    write_json(ROOT / 'app/src/main/assets/device_profile.json', report)
    (MODULE / 'device-profile.sh').write_text(
        '#!/system/bin/sh\n'
        + f"MUSE_MODEL='{report['model']}'\nMUSE_FIRMWARE='{report['firmware']}'\n"
        + f"MUSE_CAMERA_SHA256='{report['apk_sha256']}'\nMUSE_ALGO_SHA256='{report['algo_sha256']}'\n"
        + 'muse_device_matches() {\n'
        + '    [ "$(getprop ro.product.model)" = "$MUSE_MODEL" ] &&\n'
        + '    [ "$(getprop ro.build.display.id)" = "$MUSE_FIRMWARE" ] &&\n'
        + '    [ "$(sha256sum /product/app/OplusCamera/OplusCamera.apk | cut -d " " -f 1)" = "$MUSE_CAMERA_SHA256" ] &&\n'
        + '    [ "$(sha256sum /odm/lib64/libAlgoInterface.so | cut -d " " -f 1)" = "$MUSE_ALGO_SHA256" ]\n'
        + '}\n'
        + 'muse_mounts_match() {\n'
        + ''.join('    [ "$(sha256sum ' + path + ' | cut -d " " -f 1)" = "' + digest + '" ] || return 1\n'
                  for path, digest in report['mounted_files'].items())
        + '    return 0\n}\n')
    write_json(ROOT / 'evidence/merge-report.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
