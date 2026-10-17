"""Restrict UI input to the selected phone and the expected foreground package."""
import os
import fcntl
import functools
from pathlib import Path
import re
import shutil
import subprocess
import time
import tempfile
import shlex
import xml.etree.ElementTree as ET

ADB = [shutil.which('adb') or 'adb', '-s', os.environ['MUSE_DEVICE_SERIAL']]
DISMISSED_POPUPS = []


def exclusive_ui(function):
    @functools.wraps(function)
    def guarded(*args, **kwargs):
        path = Path(tempfile.gettempdir()) / ('omnicam-muse-ui-' + os.environ['MUSE_DEVICE_SERIAL'] + '.lock')
        with path.open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError('Another Muse device operation is still running') from error
            return function(*args, **kwargs)
    return guarded


def focus():
    text = subprocess.check_output(ADB + ['shell', 'dumpsys', 'window'], text=True)
    current = next((line.strip() for line in text.splitlines() if 'mCurrentFocus=' in line), '')
    if ' PopupWindow:' in current:
        # Native popups omit their package in WindowManager's focus title.
        # Require the exact focused input window's owning activity instead.
        identity = re.search(r'Window\{([^ ]+)', current)
        windows = subprocess.check_output(ADB + ['shell', 'dumpsys', 'input'], text=True)
        for line in windows.splitlines():
            if identity and ' name=' + identity.group(1) + ' ' in line and 'applicationInfo.name=' in line:
                owner = re.search(r'applicationInfo\.name=ActivityRecord\{[^}]*? ([A-Za-z][A-Za-z0-9_.]*/[^ }\t,]+)', line)
                if owner:
                    return current + ' ' + owner.group(1)
    return current


def snapshot():
    path = '/data/local/tmp/omnicam_muse_probe/window.xml'
    subprocess.run(ADB + ['shell', 'uiautomator', 'dump', path], check=True, capture_output=True)
    return ET.fromstring(subprocess.check_output(ADB + ['exec-out', 'cat', path]))


def touch(package, action, *args):
    current = focus()
    if ' ' + package + '/' not in current:
        raise RuntimeError('UI input cancelled: ' + current)
    if action not in ['tap', 'swipe', 'keyevent', 'text']:
        raise ValueError(action)
    subprocess.run(ADB + ['shell', 'input', action, *map(str, args)], check=True)


def tap_node(package, node):
    x1, y1, x2, y2 = map(int, re.findall(r'\d+', node.get('bounds')))
    touch(package, 'tap', (x1 + x2) // 2, (y1 + y2) // 2)


def physical_swipe(package, x1, y1, x2, y2, duration=450):
    """Bounded PME110 touchscreen probe; custom camera bars ignore injected MOVE events."""
    if package != 'com.oplus.camera' or ' ' + package + '/' not in focus():
        raise RuntimeError('Physical gesture requires the expected camera foreground')
    assert all(type(v) is int for v in [x1, y1, x2, y2, duration])
    assert 0 <= min(x1, x2) <= max(x1, x2) < 1216
    assert 0 <= min(y1, y2) <= max(y1, y2) < 2640 and 100 <= duration <= 1000
    command = '/data/local/tmp/omnicam_muse_probe/touch-probe ' + ' '.join(map(str, [x1, y1, x2, y2, duration]))
    result = subprocess.check_output(ADB + ['exec-out', shlex.join(['su', '-c', command])], text=True).strip()
    if result != 'Touch gesture completed and released':
        raise RuntimeError('Physical gesture failed: ' + result)


def camera_snapshot():
    # User confirmed this exact overlay opens automatically during camera tests.
    # Dismiss only this known activity, and only with an explicit per-run flag.
    if os.environ.get('MUSE_DISMISS_AUTO_BOOM') == '1' and \
            'app.textboom.revived/com.smartisan.textboom.ui.boom.BoomActivity' in focus():
        touch('app.textboom.revived', 'keyevent', 4)
        DISMISSED_POPUPS.append('BigBang')
        for _ in range(16):
            time.sleep(.5)
            current = focus()
            if ' com.oplus.camera/' in current:
                break
            if current and 'mCurrentFocus=null' not in current and 'app.textboom.revived/' not in current:
                raise RuntimeError('Unexpected foreground after automatic popup: ' + current)
    if 'com.oplus.camera/com.oplus.camera.setting.ScreenOffActivity' in focus():
        # This observed vendor activity only shows "点击屏幕恢复显示".
        touch('com.oplus.camera', 'tap', 608, 1300)
        for _ in range(16):
            time.sleep(0.5)
            current = focus()
            if ' com.oplus.camera/' in current and 'ScreenOffActivity' not in current:
                break
            if current and 'mCurrentFocus=null' not in current and ' com.oplus.camera/' not in current:
                raise RuntimeError('Camera wake interrupted: ' + current)
    current = focus()
    if ' com.oplus.camera/' not in current or 'ScreenOffActivity' in current:
        raise RuntimeError('Camera preview is not foreground: ' + current)
    return snapshot()
