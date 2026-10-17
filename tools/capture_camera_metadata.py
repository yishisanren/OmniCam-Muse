"""Read current camera-service metadata; no injected hooks or persistent flags."""
import datetime
import json
import re
import subprocess
import sys
from install_x9spro import ROOT, ADB

STANDARD = {
    'android.control.zoomRatio', 'android.scaler.cropRegion',
    'android.logicalMultiCamera.activePhysicalId', 'android.sensor.pixelMode',
    'android.control.captureIntent', 'android.control.aeTargetFpsRange',
    'android.sensor.exposureTime', 'android.sensor.sensitivity', 'android.sensor.timestamp',
    'android.lens.focalLength',
    'android.control.videoStabilizationMode', 'android.lens.opticalStabilizationMode',
}


def relevant(name):
    return name in STANDARD or (name.startswith(('com.mediatek.', 'com.oplus.')) and
        any(part in name.lower() for part in ['zoom', 'sensorscenario', 'cropregion', 'filter.type',
            'video.log', 'videolog', 'olog', 'stabilization', '.eis.']))


def capture(label):
    assert label.replace('-', '').isalnum()
    text = subprocess.check_output(ADB + ['shell', 'dumpsys', 'media.camera'], text=True)
    out = ROOT / 'evidence/experiments-20261017'
    (out / (label + '-camera-service.txt')).write_text(text)
    assert 'Client package: com.oplus.camera' in text, 'Expected active system camera'
    section, current = None, None
    values = {'received': {}, 'request': {}}
    for line in text.splitlines():
        if line.strip() in ['Latest received frame:', 'Last request sent:']:
            section = 'received' if 'received' in line else 'request'
            current = None
            continue
        match = re.match(r'\s{8}(\S+) \([0-9a-f]+\): (\w+)\[(\d+)\]', line)
        if match:
            current = match.group(1) if section and relevant(match.group(1)) else None
            if current:
                values[section][current] = []
            continue
        if current and re.match(r'\s{10}\[', line):
            raw = line.strip().strip('[] ').split()
            for item in raw:
                try:
                    values[section][current].append(float(item) if '.' in item or 'e' in item.lower() else int(item, 0))
                except ValueError:
                    values[section][current].append(item)
        elif line.strip() and not line.startswith('          '):
            current = None
    assert values['received'].get('android.sensor.timestamp'), 'Missing live received frame'
    report = {'captured_at': datetime.datetime.now().isoformat(), **values}
    (out / (label + '-camera-metadata.json')).write_text(json.dumps(report, indent=2) + '\n')
    received = values['received']
    physical = received.get('android.logicalMultiCamera.activePhysicalId', [])
    if physical and all(type(v) is int and 0 <= v <= 255 for v in physical):
        physical = bytes(physical).decode('ascii', errors='replace').strip('\0')
    print(json.dumps({'label': label, 'zoom': received.get('android.control.zoomRatio'),
        'physical': physical, 'crop': received.get('android.scaler.cropRegion'),
        'scenario': received.get('com.mediatek.seamlessfeature.sensorScenario'),
        'scenario_hint': received.get('com.mediatek.seamlessfeature.sensorScenarioCustomHint'),
        'fps': received.get('android.control.aeTargetFpsRange'),
        'iso': received.get('android.sensor.sensitivity')}))
    return report


if __name__ == '__main__':
    capture(sys.argv[1])
