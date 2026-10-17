"""Decode every frame at its original time base and check 4K60 packet timing."""
import json
from pathlib import Path
import subprocess
import sys
import numpy as np


def verify_video(path, expected_fps=60, monochrome=False):
    assert expected_fps in [30, 60]
    path = Path(path)
    probe = subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                                     '-of', 'json', str(path)], text=True)
    details = json.loads(probe)
    video = next(s for s in details['streams'] if s['codec_type'] == 'video')
    assert sorted([video['width'], video['height']]) == [2160, 3840], 'Expected 4K'
    numerator, denominator = map(int, video['avg_frame_rate'].split('/'))
    assert expected_fps - 1 <= numerator / denominator <= expected_fps + 1, f'Expected {expected_fps} fps'
    assert float(video['duration']) >= 20, 'Recording is too short'
    packet_json = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'packet=pts_time,dts_time', '-of', 'json', str(path)], text=True)
    packets = json.loads(packet_json)['packets']
    timing = {}
    for key in ['pts_time', 'dts_time']:
        values = [float(p[key]) for p in packets]
        deltas = [b - a for a, b in zip(values, values[1:])]
        assert deltas and all(d > 0 for d in deltas), 'Non-monotonic source timestamps'
        assert max(deltas) < 0.05, 'Unexpected frame gap'
        timing[key] = {'packets': len(values), 'min_delta': min(deltas), 'max_delta': max(deltas)}
    # The null output otherwise rounds ~60fps camera timestamps to a 60000/1001
    # encoder time base, producing false duplicate-DTS muxer errors. Retain the
    # demuxer's original precision; timestamp validation above remains explicit.
    decode = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-fps_mode', 'passthrough',
        '-enc_time_base', 'demux', '-f', 'null', '-'], capture_output=True, text=True)
    path.with_name(path.stem + '-decode.log').write_text(decode.stderr)
    assert decode.returncode == 0 and not decode.stderr.strip(), 'Video full decode failed'
    pixels = []
    for second in [1, float(video['duration']) / 2, float(video['duration']) - 1]:
        raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', str(second), '-i', str(path),
            '-vf', 'scale=320:180', '-frames:v', '1', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'])
        frame = np.frombuffer(raw, dtype=np.uint8).reshape(180, 320, 3).astype(float)
        mean, std = frame.mean(axis=(0, 1)), frame.std(axis=(0, 1))
        chroma = float((abs(frame[:, :, 0] - frame[:, :, 1]) + abs(frame[:, :, 1] - frame[:, :, 2])).mean())
        assert not (mean[1] > 40 and mean[0] < 5 and mean[2] < 5), 'Video has zero-plane green output'
        assert float(std.max()) > 2, 'Test scene disappeared into a flat frame'
        if monochrome:
            assert chroma < 2, 'Selected monochrome filter did not affect recorded pixels'
        pixels.append({'second': second, 'mean_rgb': mean.tolist(), 'std_rgb': std.tolist(), 'chroma': chroma})
    return {**details, 'expected_fps': expected_fps, 'expected_monochrome': monochrome,
            'pixel_samples': pixels, 'source_timing': timing, 'full_decode': True}


if __name__ == '__main__':
    result = verify_video(sys.argv[1])
    output = Path(sys.argv[1]).with_suffix('.verification.json')
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'report': str(output), 'full_decode': result['full_decode'],
                      'source_timing': result['source_timing']}))
