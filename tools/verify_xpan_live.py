"""Inspect the actual embedded XPAN clip, including reveal frames and shutter audio."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import array
from PIL import Image, ImageChops, ImageStat


def atoms(data, start, end):
    while start < end:
        assert start + 8 <= end, 'Truncated MP4 atom'
        size, kind = struct.unpack_from('>I4s', data, start)
        header = 8
        if size == 1:
            assert start + 16 <= end
            size = struct.unpack_from('>Q', data, start + 8)[0]
            header = 16
        elif size == 0:
            size = end - start
        assert header <= size <= end - start, 'Invalid MP4 atom size'
        yield kind, start + header, start + size
        start += size


def verify(path):
    path = Path(path)
    data = path.read_bytes()
    assert data[:2] == b'\xff\xd8', 'Expected the saved JPEG container'
    candidates = []
    pos = 0
    while True:
        pos = data.find(b'ftyp', pos + 1)
        if pos < 4:
            break
        start = pos - 4
        try:
            # Camera extension data can follow the MP4. Stop after the moov/mdat
            # pair instead of interpreting another extension as an MP4 atom.
            found, end = set(), start
            for kind, payload, after in atoms(data, start, len(data)):
                found.add(kind)
                end = after
                if {b'ftyp', b'moov', b'mdat'} <= found:
                    break
            if {b'ftyp', b'moov', b'mdat'} <= found:
                candidates.append(data[start:end])
        except (AssertionError, struct.error):
            continue
    assert len(candidates) == 1, 'Expected exactly one embedded MP4'
    clip = candidates[0]
    extension = None
    for kind, start, end in atoms(clip, 0, len(clip)):
        if kind == b'moov':
            for child, payload, after in atoms(clip, start, end):
                if child == b'lpex':
                    raw = clip[payload:after]
                    assert raw.startswith(b'LivePhotoExtension')
                    extension = json.loads(raw[len(b'LivePhotoExtension'):])
    assert extension is not None, 'Missing the gallery LivePhotoExtension'
    video = path.with_suffix('.embedded.mp4')
    video.write_bytes(clip)
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames',
        '-show_streams', '-show_format', '-of', 'json', str(video)], text=True))
    stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    # The encoder includes frame zero: 75 reveal intervals + 9 hold frames + 1.
    expected_frames = 75 + 9 + 1
    assert int(stream['nb_read_frames']) == expected_frames, 'Incomplete developing animation'
    assert max(stream['width'], stream['height']) <= 2160
    assert abs(float(stream['duration']) - 2.8) < .1
    assert audio['codec_name'] == 'aac'
    pcm = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(video),
        '-vn', '-ac', '1', '-ar', '16000', '-f', 's16le', '-'])
    samples = array.array('h', pcm)
    assert samples and max(map(abs, samples)) > 100, 'Missing audible shutter signal'
    decode = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-fps_mode', 'passthrough',
        '-enc_time_base', 'demux', '-f', 'null', '-'], capture_output=True, text=True)
    assert decode.returncode == 0 and not decode.stderr.strip(), 'Embedded clip decode failed'
    # Preserve first/last frames for visual confirmation of negative-to-photo reveal.
    for label, frame in [('first', 0), ('last', expected_frames - 1)]:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(video), '-vf',
            'select=eq(n\\,' + str(frame) + ')', '-frames:v', '1',
            str(path.with_name(path.stem + '-' + label + '.png'))], check=True)
    first = Image.open(path.with_name(path.stem + '-first.png')).convert('RGB')
    last = Image.open(path.with_name(path.stem + '-last.png')).convert('RGB')
    assert first.size == last.size
    box = (first.width // 5, first.height // 5, first.width * 4 // 5, first.height * 4 // 5)
    difference = ImageStat.Stat(ImageChops.difference(first.crop(box), last.crop(box))).mean
    assert sum(difference) / 3 > 20, 'Clip is static instead of revealing the negative'
    report = {'container_sha256': hashlib.sha256(data).hexdigest(),
              'clip_sha256': hashlib.sha256(clip).hexdigest(), 'clip': str(video),
              'video': stream, 'audio': audio, 'extension': extension, 'full_decode': True,
              'audio_peak_pcm16': max(map(abs, samples)), 'first_last_mean_difference': difference}
    path.with_suffix('.live-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'frames': stream['nb_read_frames'], 'duration': stream['duration'],
        'size': [stream['width'], stream['height']], 'audio': audio['codec_name'], 'full_decode': True}))


if __name__ == '__main__':
    verify(sys.argv[1])
