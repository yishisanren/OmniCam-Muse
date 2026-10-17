"""Use PME110's public forward matrices with a neutral HueSatMap, never Ultra DCPs.

This is a device-native matrix profile, not an Adobe Standard DCP calibration.
Android's SENSOR_FORWARD_MATRIX maps white-balanced reference camera RGB to XYZ D50.
https://developer.android.com/reference/android/hardware/camera2/CameraCharacteristics#SENSOR_FORWARD_MATRIX1
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
KELVIN = {17: 2856.0, 21: 6504.0}


def main():
    capture = Path(os.environ.get('MUSE_CAPTURE_DIR', ROOT / 'evidence/device-20261017'))
    profiles = json.loads((capture / 'camera-characteristics.json').read_text())
    ids = sorted(profiles['0']['physical_ids'])
    if ids != ['2', '3', '4']:
        raise ValueError('Unexpected physical rear camera IDs')
    blob = b'MCSCENE1' + struct.pack('<II', 1, len(ids))
    report = []
    for camera in ids:
        row = profiles[camera]
        assert row['facing'] == 1 and not row['physical_ids']
        name = ('camera' + camera).encode('ascii')
        temperatures = [KELVIN[row['illuminant1']], KELVIN[row['illuminant2']]]
        assert temperatures[0] != temperatures[1]
        blob += struct.pack('<I', len(name)) + name + struct.pack('<3f', row['equivalent_focal'], *temperatures)
        for index in [1, 2]:
            calibration = np.array(row['calibration' + str(index)]).reshape(3, 3)
            assert np.allclose(calibration, np.eye(3), atol=1e-6)
            matrix = np.array(row['forward' + str(index)]).reshape(3, 3)
            assert np.isfinite(matrix).all() and abs(np.linalg.det(matrix)) > 1e-6
            assert np.allclose(matrix @ np.ones(3), [0.9642, 1.0, 0.8252], atol=0.002)
            blob += matrix.astype('<f4').tobytes()
        blob += struct.pack('<3I', 2, 2, 1)
        blob += struct.pack('<12f', *([0, 1, 1] * 4)) * 2
        report.append({'id': camera, 'focal': row['equivalent_focal']})
    target = ROOT / 'module/payload/master_color/scene.bin'
    target.write_bytes(blob)
    result = {'kind': 'device-native forward matrices with neutral HueSatMap', 'lenses': report,
              'sha256': hashlib.sha256(blob).hexdigest(), 'colorimetric_validation': 'not performed'}
    (ROOT / 'evidence/scene-profile.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
