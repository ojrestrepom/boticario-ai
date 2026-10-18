"""Native QA helpers, restricted to the explicitly authorized AVD; no product edits.

Requires an external private temp directory with baseline.json from preflight.
No web/API: Playwright and Postman do not apply to this native-only screen.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET

QA = Path(__file__).resolve().parent
REPO = QA.parents[4]
TEMP = Path(os.environ["QA_PRIVATE_TEMP"])
ADB = str(Path.home() / "Library/Android/sdk/platform-tools/adb")
SERIAL = "emulator-5566"
PACKAGE = "com.example.boticario_ai"
EVIDENCE = QA / "evidence"


def adb(*args, binary=False, check=True):
    p = subprocess.run([ADB, "-s", SERIAL, *map(str, args)], capture_output=True, check=check)
    return p.stdout if binary else p.stdout.decode().strip()


def guard():
    identity = dict(state=adb("get-state"), avd=adb("emu", "avd", "name").splitlines()[0],
                    api=adb("shell", "getprop", "ro.build.version.sdk"),
                    boot=adb("shell", "getprop", "sys.boot_completed"))
    assert identity == dict(state="device", avd="boticario_catalog_api36", api="36", boot="1"), identity
    return identity


def settings():
    return {f"{ns}.{key}": adb("shell", "settings", "get", ns, key) for ns, key in
            [("system", "font_scale"), ("global", "wifi_on"), ("global", "mobile_data"),
             ("global", "airplane_mode_on"), ("secure", "accessibility_enabled"),
             ("secure", "touch_exploration_enabled")]}


def tree():
    raw = adb("exec-out", "uiautomator", "dump", "/dev/tty")
    start = raw.find("<?xml")
    end = raw.find("</hierarchy>") + len("</hierarchy>")
    assert start >= 0 and end > start, raw
    return raw[start:end]


def nodes(xml=None):
    return [n.attrib for n in ET.fromstring(xml or tree()).iter("node")]


def bounds(node):
    return tuple(map(int, re.findall(r"\d+", node["bounds"])))


def find(label, xml=None):
    found = [n for n in nodes(xml) if n.get("content-desc") == label or n.get("text") == label]
    assert len(found) == 1, (label, found)
    return found[0]


def tap(label):
    x1, y1, x2, y2 = bounds(find(label))
    adb("shell", "input", "tap", (x1+x2)//2, (y1+y2)//2)


def scroll_up():
    adb("shell", "input", "swipe", 540, 1400, 540, 650, 500)


def capture(name):
    assert name.startswith("manual-P06")
    EVIDENCE.mkdir(exist_ok=True)
    xml = tree()
    (EVIDENCE / f"{name}.xml").write_text(xml)
    (EVIDENCE / f"{name}.png").write_bytes(adb("exec-out", "screencap", "-p", binary=True))
    print(name)
    for n in nodes(xml):
        label = n.get("content-desc") or n.get("text")
        if label:
            print(label, n["bounds"], "clickable="+n["clickable"], "enabled="+n["enabled"], "selected="+n["selected"])
    return xml


def restore_font():
    guard()
    original = json.loads((TEMP / "baseline.json").read_text())["settings"]["system.font_scale"]
    if original == "null":
        adb("shell", "settings", "delete", "system", "font_scale")
    else:
        adb("shell", "settings", "put", "system", "font_scale", original)
    assert settings()["system.font_scale"] == original


def redact(text):
    # VM service URLs contain authentication path tokens; never version them.
    return re.sub(r"(?:https?|wss?)://(?:127\.0\.0\.1|localhost|\[::1\]):\d+/[^\s]*",
                  "[REDACTED_VM_SERVICE_URL]", text)


def manifest():
    files = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others",
                                     "--exclude-standard", "app"], cwd=REPO).decode().split("\0")
    return {p: hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in sorted(set(filter(None, files)))
            if (REPO/p).is_file()}


if __name__ == "__main__":
    print(json.dumps({"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      "identity": guard(), "settings": settings()}, indent=2))
