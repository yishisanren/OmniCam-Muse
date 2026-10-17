"""Fast hardware feedback: require the native capture/soften path, not a visible UI switch."""
import sys
from install_x9spro import root


def main():
    feature = sys.argv[1]
    prefix = '/data/user/0/com.oplus.camera/files/jiege/'
    if feature in ['master', 'master-colour']:
        status = root('cat ' + prefix + 'mastercolor/capture-status').decode().strip()
        print(status)
        assert 'baked=1' in status, 'Master capture did not apply the selected colour table'
        assert 'gamma=257' in status
        assert '/live/m' in status, 'Only a thumbnail was baked; main capture has not completed'
        applied = root('cat ' + prefix + 'mastercolor/applied-status').decode().strip()
        print(applied)
        assert 'LMT applied:' in applied, 'BasicTone did not load the baked table'
        assert '/live/m' in applied, 'Only a thumbnail table was selected'
        if feature == 'master-colour':
            expected_lens = sys.argv[2]
            assert expected_lens in ['camera2', 'camera3', 'camera4']
            assert 'lens=' + expected_lens + ' ' in status, 'Wrong physical calibration profile'
            from PIL import Image, ImageStat
            image = Image.open(sys.argv[3]).convert('L')
            image.thumbnail((300, 400))
            stats = ImageStat.Stat(image)
            print('Final JPEG mean/std:', stats.mean[0], stats.stddev[0])
            assert 5 < stats.mean[0] < 240 and stats.stddev[0] > 2, 'Gross exposure or missing scene'
            return
        # A native status can report a selected path even when vendor LUT naming
        # causes a fallback. Require the actual final monochrome JPEG as proof.
        from pathlib import Path
        from PIL import Image, ImageChops, ImageStat
        image = Image.open(Path(sys.argv[2])).convert('RGB')
        image = image.crop((0, 0, image.width, int(image.height * .9)))
        image.thumbnail((400, 400))
        r, g, b = image.split()
        chroma = ImageStat.Stat(ImageChops.difference(r, g)).mean[0] + ImageStat.Stat(ImageChops.difference(g, b)).mean[0]
        print('Final JPEG chroma:', chroma)
        assert chroma < 2, 'Selected monochrome look did not affect final full-size pixels'
        if len(sys.argv) > 3:
            control = Image.open(Path(sys.argv[3])).convert('L')
            control = control.crop((0, 0, control.width, int(control.height * .9)))
            actual_y = ImageStat.Stat(image.convert('L')).mean[0]
            control_y = ImageStat.Stat(control).mean[0]
            ratio = actual_y / max(control_y, 1)
            print('Mean luminance look/control:', actual_y, control_y, ratio)
            assert .25 < ratio < 4, 'The look introduced a gross exposure error in the fixed-scene comparison'
    elif feature == 'soft-light':
        import re
        expected = sys.argv[2]
        assert expected in ['HDF', 'black-mist', 'white-mist']
        status = root('cat ' + prefix + 'soft-light-status').decode().strip()
        print(status)
        assert 'filter=' + expected + ' ' in status, 'The selected physical filter did not run'
        applied = re.search(r'applied=(\d+)', status)
        assert applied and int(applied.group(1)) > 0
        assert 'format=0x36 ' in status and 'last=1 ' in status and 'result=1' in status, 'P010 soft-light processing failed'
        size = re.search(r'size=(\d+)x(\d+)', status)
        assert size and min(map(int, size.groups())) > 2000, 'Only preview/thumbnail processing was verified'
    elif feature in ['soften', 'soften-isolated']:
        status = root('cat ' + prefix + 'natural/status').decode().strip()
        print(status)
        assert 'backend: MTK-OpenCL ready=1' in status, 'MTK guided-filter hook is not ready'
        import re
        changed = re.search(r'changed=(\d+)', status)
        assert changed
        if feature == 'soften-isolated':
            assert int(changed.group(1)) == 0, 'Extra softening leaked into another mode'
            return
        percent = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        assert 0 <= percent <= 100
        assert (int(changed.group(1)) > 0) == (percent > 0), 'Softening enabled state does not match the requested value'
        result = re.search(r'result=(-?\d+)', status)
        assert result and int(result.group(1)) == 0, 'The guided-filter kernel did not complete successfully'
        epsilon = re.search(r'eps: stock=([\deE.+-]+) applied=([\deE.+-]+)', status)
        assert epsilon, 'Missing actual kernel values'
        stock, applied = map(float, epsilon.groups())
        expected = 10 ** (4 * percent / 100)
        assert stock > 0 and abs(applied / stock / expected - 1) < .002, 'Actual softening strength does not match the requested value'
    else:
        raise ValueError(feature)


if __name__ == '__main__':
    main()
