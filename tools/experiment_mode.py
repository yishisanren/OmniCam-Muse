"""Navigate only through observed camera controls and assert every mode transition."""
import subprocess
import sys
import time
from device_actions import ADB, camera_snapshot, tap_node, touch, focus, exclusive_ui


def mode():
    tree = camera_snapshot()
    if any(n.get('resource-id') == 'com.oplus.camera:id/xpan_guide_title' and
           n.get('text') == '全新 XPAN 仪式感升级' for n in tree.iter('node')):
        acknowledge = next(n for n in tree.iter('node') if n.get('resource-id') ==
                           'android:id/button1' and n.get('text') == '知道了')
        tap_node('com.oplus.camera', acknowledge)
        time.sleep(2)
        tree = camera_snapshot()
    names = [n.get('content-desc', '') for n in tree.iter('node')
             if n.get('resource-id') in ['com.oplus.camera:id/headline_view', 'com.oplus.camera:id/preview_talkback']]
    return tree, ' '.join(names)


def select(x, expected):
    _, before = mode()
    touch('com.oplus.camera', 'tap', x, 2440)
    time.sleep(2)
    tree, name = mode()
    if expected not in name and name == before:
        touch('com.oplus.camera', 'tap', x, 2440)
        time.sleep(2)
        tree, name = mode()
    assert expected in name, (expected, name)
    return tree


@exclusive_ui
def main():
    wanted = sys.argv[1]
    assert wanted in ['照片', '视频', 'POP', '理光 GR', '哈苏超清', '大师', 'XPAN', '专业视频']
    previous = None
    for _ in range(16):
        current = focus()
        if current == previous and 'mCurrentFocus=null' not in current:
            break
        previous = current
        time.sleep(.5)
    # Viewing the exact MediaStore URI can add another Gallery viewer above
    # the one opened by Camera. Leave only those known read-only viewers.
    for _ in range(4):
        if ' com.coloros.gallery3d/com.oppo.gallery3d.app.ViewGallery' not in focus():
            break
        touch('com.coloros.gallery3d', 'keyevent', 4)
        time.sleep(1)
    if ' com.oplus.camera/' not in focus():
        subprocess.run(ADB + ['shell', 'am', 'start', '-W', '-a', 'android.media.action.STILL_IMAGE_CAMERA'], check=True, capture_output=True)
        time.sleep(2)
    for _ in range(12):
        current = focus()
        if ' com.oplus.camera/' in current:
            break
        if current and 'mCurrentFocus=null' not in current and 'com.android.launcher' not in current:
            raise RuntimeError('Camera launch interrupted: ' + current)
        time.sleep(1)
    tree, name = mode()
    if wanted + '模式' in name:
        print(name)
        return
    # Returning from Gallery can leave a filter palette in front of the mode
    # selector. Close only its observed back control before changing modes.
    for _ in range(3):
        palette_back = next((n for n in tree.iter('node') if n.get('resource-id') ==
                             'com.oplus.camera:id/effect_style_back_icon'), None)
        if palette_back is None:
            break
        tap_node('com.oplus.camera', palette_back)
        time.sleep(1)
        tree, name = mode()
    special = next((n for n in tree.iter('node') if n.get('resource-id') == 'com.oplus.camera:id/mode_title_layout'), None)
    if special is not None:
        tap_node('com.oplus.camera', special)
        time.sleep(1)
        tree, name = mode()
    if '哈苏超清模式' in name:
        tree = select(110, '理光 GR模式')
        name = '理光 GR模式'
    if '理光 GR模式' in name:
        select(360, '照片模式')
        name = '照片模式'
    if '视频模式' in name:
        select(830, '照片模式')
        name = '照片模式'
    if 'POP模式' in name:
        select(1050, '照片模式')
        name = '照片模式'
    assert '照片模式' in name, name
    if wanted == '照片':
        print(name)
        return
    if wanted == 'POP':
        select(165, 'POP模式')
    elif wanted == '视频':
        select(390, '视频模式')
    else:
        select(860, '理光 GR模式')
        if wanted != '理光 GR':
            select(1080, '哈苏超清模式')
            if wanted != '哈苏超清':
                tree = select(850, '更多模式')
                tap_node('com.oplus.camera', next(n for n in tree.iter('node') if n.get('content-desc') == wanted))
                time.sleep(2)
    _, name = mode()
    assert wanted + '模式' in name, (wanted, name)
    print(name)


if __name__ == '__main__':
    main()
