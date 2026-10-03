#!/usr/bin/env python3
"""Read-only evidence checks; writes only authorized android-manual evidence."""
import collections
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
EV = Path(__file__).resolve().parent / 'evidence'
lines = [datetime.datetime.now(datetime.timezone.utc).isoformat()]
before = (EV / 'android-manual-before-manifest.txt').read_text().splitlines()
after = (EV / 'android-manual-after-manifest.txt').read_text().splitlines()
lines += ['MANIFEST removed/changed: ' + repr(sorted(set(before) - set(after))),
          'MANIFEST added/changed: ' + repr(sorted(set(after) - set(before)))]
apk = ROOT / 'app/build/app/outputs/flutter-apk/app-debug.apk'
lines.append('APK SHA256 ' + hashlib.sha256(apk.read_bytes()).hexdigest())
restores = 0
for path in sorted(EV.glob('android-manual-*-settings-after.json')):
    pre = path.with_name(path.name.replace('-settings-after.json', '-settings-before.json'))
    result = json.loads(path.read_text()) == json.loads(pre.read_text())
    lines.append('RESTORE ' + path.name + ' ' + str(result))
    restores += result
lines.append('RESTORATIONS matched ' + str(restores))
for path in sorted(EV.glob('android-manual-*-pid-*.log')):
    text = path.read_text()
    messages = re.findall(r'\[Home\][^\r\n]*', text)
    lines.append('LOG ' + path.name + ' HOME=' + repr(dict(collections.Counter(messages))) +
                 ' marker=' + str('QA_SYNTH_20261003_NO_MATCH' in text) +
                 ' harness=' + str('[CatalogSmoke' in text))
    errors = [line for line in text.splitlines() if any(s in line for s in ['FATAL EXCEPTION', 'Unhandled Exception', 'RenderFlex overflowed', 'EXCEPTION CAUGHT BY'])]
    lines.append('LOG errors ' + repr(errors))
for name in ['return100-before', 'return100-chevron-after', 'return100-android-after']:
    nodes = ET.fromstring((EV / ('android-manual-' + name + '.xml')).read_text())
    rows = [(n.get('content-desc'), n.get('bounds')) for n in nodes.iter('node')
            if n.get('content-desc', '').startswith(('Lavanda,', 'Eucalipto,', 'Romero,', 'Manzanilla,', 'Menta,'))]
    selected = [n.get('content-desc') for n in nodes.iter('node') if n.get('selected') == 'true']
    query = [n.get('text') for n in nodes.iter('node') if n.get('class') == 'android.widget.EditText']
    lines.append('RETURN ' + name + ' rows=' + repr(rows) + ' selected=' + repr(selected) + ' query=' + repr(query))
for name in ['home100-cold', 'explore100-top', 'menta100-top', 'explore200-valid-top', 'menta200-full-top']:
    nodes = ET.fromstring((EV / ('android-manual-' + name + '.xml')).read_text())
    lines.append('NATIVE SEMANTICS ' + name + ' (bounds px; dp=px/3; viewport may clip offscreen rows)')
    for n in nodes.iter('node'):
        if n.get('package') != 'com.example.boticario_ai':
            continue
        if n.get('clickable') == 'true' or 'no disponible' in n.get('content-desc', ''):
            lines.append(repr({key: n.get(key) for key in ['class', 'text', 'hint', 'content-desc', 'enabled', 'clickable', 'selected', 'bounds']}))
lines.append('GIT STATUS (read-only):\n' + subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True))
procs = subprocess.check_output(['ps', '-axo', 'pid,command'], text=True)
lines.append('AVD PROCESS:\n' + '\n'.join(s for s in procs.splitlines() if 'qemu-system' in s and 'boticario_catalog_api36' in s))
lines.append('CONCURRENT TOOLING:\n' + '\n'.join(s for s in procs.splitlines() if ('flutter_tools' in s and any(x in s for x in [' run ', ' test ', ' drive '])) or ('platform-tools/adb' in s and 'emulator-5566' in s)))
(EV / 'android-manual-summary.txt').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
