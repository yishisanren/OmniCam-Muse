"""Set only named test preferences while the writer and camera are stopped."""
import json
from pathlib import Path
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET
from install_x9spro import ADB, ROOT, root
from device_actions import exclusive_ui


@exclusive_ui
def main():
    values = json.loads(sys.argv[1])
    assert isinstance(values, dict) and values
    source = ROOT / 'app/src/main/java/local/jiege/settings/ModuleSettings.java'
    allowed = source.read_text()
    for key in values:
        assert '"' + key + '"' in allowed, key
    baseline = json.loads((ROOT / 'evidence/experiments-20261017/before.json').read_text())
    path = baseline['module_preferences']
    root('am force-stop local.jiege.camera; am force-stop com.oplus.camera')
    tree = ET.fromstring(root('cat ' + shlex.quote(path)))
    for key, value in values.items():
        previous = next((n for n in tree if n.get('name') == key), None)
        if previous is not None:
            tree.remove(previous)
        if type(value) is bool:
            ET.SubElement(tree, 'boolean', name=key, value=str(value).lower())
        elif type(value) is int:
            ET.SubElement(tree, 'int', name=key, value=str(value))
        elif type(value) is str:
            ET.SubElement(tree, 'string', name=key).text = value
        else:
            raise ValueError(key)
    local = ROOT / 'evidence/experiments-20261017/settings-staged.xml'
    local.write_bytes(ET.tostring(tree, encoding='utf-8', xml_declaration=True))
    remote = '/data/local/tmp/omnicam_muse_probe/experiment-settings.xml'
    subprocess.run(ADB + ['push', str(local), remote], check=True, capture_output=True)
    # Write into the existing inode so LSPosed's uid, mode and SELinux label remain intact.
    root('cat ' + shlex.quote(remote) + ' > ' + shlex.quote(path))
    actual = ET.fromstring(root('cat ' + shlex.quote(path)))
    for key, value in values.items():
        node = next(n for n in actual if n.get('name') == key)
        assert (node.get('value') or node.text) == (str(value).lower() if type(value) is bool else str(value))
    print(json.dumps({'applied_preferences': values, 'camera_stopped': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
