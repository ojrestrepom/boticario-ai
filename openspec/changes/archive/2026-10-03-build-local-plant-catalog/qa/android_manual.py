#!/usr/bin/env python3
"""Android-only QA. Never selects another device; temporary settings rollback."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
EV = Path(__file__).resolve().parent / 'evidence'
ADB = str(Path.home() / 'Library/Android/sdk/platform-tools/adb')
SERIAL = 'emulator-5566'
PKG = 'com.example.boticario_ai'
LOG = EV / 'android-manual-commands.log'

def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def record(message):
    with LOG.open('a') as out:
        out.write(stamp() + ' ' + message + '\n')

def cmd(args, binary=False):
    record('CMD ' + json.dumps(args))
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    record('EXIT ' + str(p.returncode) + ' STDERR ' + p.stderr.decode(errors='replace'))
    if not binary:
        record('OUT ' + p.stdout.decode(errors='replace'))
    p.check_returncode()
    return p.stdout if binary else p.stdout.decode().strip()

def identity():
    result = cmd([ADB, '-s', SERIAL, 'emu', 'avd', 'name'])
    if result.splitlines()[0].strip() != 'boticario_catalog_api36':
        raise RuntimeError('STOP: wrong AVD identity')

def adb(*args, binary=False):
    identity()
    return cmd([ADB, '-s', SERIAL, *map(str, args)], binary=binary)

def settings():
    return {k: adb('shell', 'settings', 'get', ns, k) for ns, k in
            [('system', 'font_scale'), ('global', 'wifi_on'), ('global', 'mobile_data')]}

def network(name):
    raw = adb('shell', 'dumpsys', 'connectivity', binary=True).decode()
    # Metadata only. No notifications, accounts, SSIDs or other apps' logs.
    import re
    lines = [s for s in raw.splitlines() if 'Active default network' in s]
    agents = [s for s in raw.splitlines() if 'NetworkAgentInfo{' in s]
    lines.append('Live network agents: ' + str(len(agents)))
    for s in agents:
        lines.append('Agent ' + (re.search(r'network\{[^}]+\}',s).group() if re.search(r'network\{[^}]+\}',s) else '?'))
        cap = re.search(r'Transports: (.*?) Capabilities: (.*?) LinkUpBandwidth',s)
        if cap: lines.append('Transports: ' + cap.group(1) + ' Capabilities: ' + cap.group(2))
        else:
            cap = re.search(r'Transports: (.*?) Capabilities: (.*?) (?:Specifier:|SubscriptionIds:|UnderlyingNetworks:)',s)
            if cap: lines.append('Transports: ' + cap.group(1) + ' Capabilities: ' + cap.group(2))
    (EV / ('android-manual-' + name + '-network.txt')).write_text('\n'.join(lines) + '\n')
    record('CONNECTIVITY_METADATA ' + '\n'.join(lines))
    return raw

def tree(name):
    remote = '/data/local/tmp/android_manual_tree.xml'
    adb('shell', 'uiautomator', 'dump', remote)
    try:
        raw = adb('shell', 'cat', remote)
    finally:
        adb('shell', 'rm', remote)
    start = raw.find('<?xml')
    end = raw.rfind('</hierarchy>') + len('</hierarchy>')
    if start < 0 or end < len('</hierarchy>'):
        raise RuntimeError('Missing accessibility tree')
    xml = raw[start:end]
    (EV / ('android-manual-' + name + '.xml')).write_text(xml)
    nodes = ET.fromstring(xml)
    print('TREE', name, 'selected=', [n.get('content-desc') for n in nodes.iter('node') if n.get('package') == PKG and n.get('selected') == 'true'])
    return nodes

def shot(name):
    tree(name)
    path = EV / ('android-manual-' + name + '.png')
    path.write_bytes(adb('exec-out', 'screencap', '-p', binary=True))
    record('SCREEN ' + str(path.relative_to(ROOT)) + ' SHA256 ' + hashlib.sha256(path.read_bytes()).hexdigest())
    return path.read_bytes()

def walk(name, maximum, duration=850):
    """Overlapping full screenshots; stop only on stable pixels, never merged text."""
    previous = shot(name + '-00')
    matches = 0
    for step in range(1, int(maximum) + 1):
        adb('shell', 'input', 'swipe', 540, 1170, 540, 370, int(duration))
        current = shot(name + '-' + str(step).zfill(2))
        matches = matches + 1 if current == previous else 0
        record('WALK ' + name + ' step=' + str(step) + ' identicalPixels=' + str(current == previous))
        if matches >= 2:
            record('WALK_STABLE ' + name + ' step=' + str(step) + ' (requires visual final-content review)')
            return
        previous = current
    raise RuntimeError('Bounded walk did not reach stable pixels: ' + name)

def logs(name):
    pid = adb('shell', 'pidof', PKG).split()
    if len(pid) != 1:
        raise RuntimeError('Expected exactly one live app PID')
    text = adb('logcat', '--pid=' + pid[0], '-d', '-v', 'threadtime')
    (EV / ('android-manual-' + name + '-pid-' + pid[0] + '.log')).write_text(text)
    record('LOG_SCOPE pid=' + pid[0])

def manifest(name):
    paths = [ROOT / '.flutter-version', ROOT / 'app/pubspec.yaml', ROOT / 'app/pubspec.lock', ROOT / 'app/analysis_options.yaml']
    for directory in ['app/lib', 'app/test', 'app/integration_test', 'app/assets', 'app/android', 'docs', 'openspec/changes/archive/2026-10-03-build-local-plant-catalog/qa']:
        paths += [p for p in (ROOT / directory).rglob('*') if p.is_file() and not any(x in p.parts for x in ['build','.gradle']) and 'android-manual' not in p.name and 'android_manual' not in p.name]
    lines = [str(p.relative_to(ROOT)) + ' ' + hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))]
    (EV / ('android-manual-' + name + '-manifest.txt')).write_text('\n'.join(lines) + '\n')

def interrupted(*_):
    raise KeyboardInterrupt('Interrupted; restoring authorized settings')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--font', choices=['1.0','2.0'])
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--actions', default='[]', help='JSON array [verb, arguments...]')
    opts = parser.parse_args()
    EV.mkdir(exist_ok=True)
    record('BEGIN ' + opts.name)
    identity()
    procs = subprocess.check_output(['ps','-axo','pid,command'], text=True)
    concurrent = [s for s in procs.splitlines() if ('flutter_tools' in s and any(x in s for x in [' run ', ' test ', ' drive '])) or ('platform-tools/adb' in s and 'emulator-5566' in s)]
    if concurrent:
        raise RuntimeError('STOP concurrent tooling: ' + '\n'.join(concurrent))
    original = settings()
    (EV / ('android-manual-' + opts.name + '-settings-before.json')).write_text(json.dumps(original, indent=2) + '\n')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    changed = bool(opts.font or opts.offline)
    try:
        if opts.font:
            adb('shell','settings','put','system','font_scale',opts.font)
            assert settings()['font_scale'] == opts.font
            tree(opts.name + '-font-ready')
        if opts.offline:
            network(opts.name + '-before')
            adb('shell','svc','wifi','disable')
            adb('shell','svc','data','disable')
            deadline = time.monotonic() + 20
            for attempt in range(100):
                raw = network(opts.name + '-offline-check-' + str(attempt))
                ready = ('Active default network: none' in raw or 'Active default network: NONE' in raw) and 'NetworkAgentInfo{' not in raw
                if ready or time.monotonic() >= deadline: break
            assert ready, 'STOP: still online; no offline PASS'
            active = settings()
            assert active['wifi_on'] == active['mobile_data'] == '0'
            (EV / ('android-manual-' + opts.name + '-settings-offline.json')).write_text(json.dumps(active,indent=2))
        if opts.build:
            identity()
            env = os.environ.copy()
            env['PATH'] = '/opt/homebrew/share/flutter/bin:' + env['PATH']
            args = ['flutter','run','--debug','--target','lib/main.dart','--no-resident','-d',SERIAL]
            record('BUILD ' + json.dumps(args))
            p = subprocess.run(args, cwd=ROOT/'app', env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
            (EV / 'android-manual-build.log').write_text(stamp() + '\n' + p.stdout.decode(errors='replace') + '\nEXIT ' + str(p.returncode) + '\n')
            p.check_returncode()
        for index, action in enumerate(json.loads(opts.actions)):
            verb, *args = action
            record('ACTION ' + json.dumps(action))
            if verb == 'shot': shot(*args)
            elif verb == 'walk': walk(*args)
            elif verb == 'activate':
                import re
                nodes = tree(opts.name + '-activate-' + str(index))
                found = [n for n in nodes.iter('node') if n.get('package') == PKG and (n.get('content-desc') == args[0] or n.get('text') == args[0])]
                assert len(found) == 1, 'Label must identify exactly one native node: ' + args[0]
                x1,y1,x2,y2 = map(int,re.findall(r'\d+',found[0].get('bounds')))
                adb('shell','input','tap',(x1+x2)//2,(y1+y2)//2)
            elif verb == 'tree': tree(*args)
            elif verb == 'logs': logs(*args)
            elif verb == 'network': network(*args)
            elif verb == 'manifest': manifest(*args)
            elif verb == 'tap': adb('shell','input','tap',*args)
            elif verb == 'swipe': adb('shell','input','swipe',*args)
            elif verb == 'motion': adb('shell','input','motionevent',*args)
            elif verb == 'back': adb('shell','input','keyevent','4')
            elif verb == 'text': adb('shell','input','text',*args)
            elif verb == 'key': adb('shell','input','keyevent',*args)
            elif verb == 'cold':
                adb('shell','am','force-stop',PKG)
                adb('shell','am','start','-n',PKG+'/.MainActivity')
                tree(opts.name + '-cold-ready')
            elif verb == 'info':
                info = {key: adb('shell',*value) for key,value in {
                    'size':['wm','size'], 'density':['wm','density'], 'android':['getprop','ro.build.version.release'],
                    'sdk':['getprop','ro.build.version.sdk'], 'package':['dumpsys','package',PKG]}.items()}
                info['package'] = '\n'.join(s for s in info['package'].splitlines() if any(t in s for t in ['versionCode=','versionName=','userId=','codePath=']))
                (EV / ('android-manual-' + opts.name + '-info.json')).write_text(json.dumps(info, indent=2))
            else: raise ValueError(verb)
    finally:
        if changed:
            # Each restore command rechecks identity; stop rather than touch a replacement AVD.
            if opts.offline:
                adb('shell','svc','wifi','enable' if original['wifi_on'] not in ['0','null'] else 'disable')
                adb('shell','svc','data','enable' if original['mobile_data'] not in ['0','null'] else 'disable')
            restore_keys = [('system','font_scale')]
            if opts.offline:
                restore_keys += [('global','wifi_on'),('global','mobile_data')]
            for ns,k in restore_keys:
                if original[k] == 'null': adb('shell','settings','delete',ns,k)
                else: adb('shell','settings','put',ns,k,original[k])
        after = settings()
        (EV / ('android-manual-' + opts.name + '-settings-after.json')).write_text(json.dumps(after, indent=2) + '\n')
        if opts.offline: network(opts.name + '-restored')
        assert after == original, 'STOP RESTORATION FAILED'
        record('RESTORED EXACT ' + json.dumps(after))
    record('END ' + opts.name)

if __name__ == '__main__':
    main()
