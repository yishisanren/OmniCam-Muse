"""Select an observed Master filter using the real, bounded camera touch region."""
import json
import re
import sys
import time
from device_actions import camera_snapshot, tap_node, physical_swipe, exclusive_ui


@exclusive_ui
def main():
    wanted = sys.argv[1]
    assert wanted and len(wanted) < 20
    r = camera_snapshot()
    assert any('大师模式' in n.get('content-desc', '') for n in r.iter('node'))
    right = next((n for n in r.iter('node') if n.get('resource-id') ==
                  'com.oplus.camera:id/camera_menu_right_enter_button'), None)
    already_open = any(n.get('resource-id') == 'com.oplus.camera:id/effect_style_filter_hint'
                       for n in r.iter('node'))
    if right is not None and not already_open:
        tap_node('com.oplus.camera', right)
        time.sleep(1)
    seen = []
    for _ in range(30):
        r = camera_snapshot()
        hint = next(n for n in r.iter('node') if n.get('resource-id') ==
                    'com.oplus.camera:id/effect_style_filter_hint')
        style = hint.get('text')
        if style == wanted:
            print(json.dumps({'selected': style, 'observed': seen}, ensure_ascii=False))
            return
        if style in seen:
            raise RuntimeError('Filter gesture did not advance or completed a full cycle: ' + str(seen))
        seen.append(style)
        _, y1, _, y2 = map(int, re.findall(r'\d+', hint.get('bounds')))
        start, end = (450, 800) if wanted == '标准' else (800, 450)
        physical_swipe('com.oplus.camera', start, (y1 + y2) // 2, end, (y1 + y2) // 2, 1000)
        time.sleep(1.5)
    raise RuntimeError('Filter not reached within bounded gestures')


if __name__ == '__main__':
    main()
