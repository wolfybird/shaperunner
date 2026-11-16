"""Checks a built app's license files; the build workflow runs it:

    python .github/check_notices.py dist/ShapeRunner
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED = ["Python ", "Tcl ", "Tk ", "numpy ", "pygame-ce ", "sounddevice ",
            "cffi ", "PortAudio "]
NOT_FOUND = "LICENSE TEXT NOT FOUND"      # what the spec writes for a gap

folder = sys.argv[1]
license_txt = os.path.join(folder, "LICENSE.txt")
notices_txt = os.path.join(folder, "THIRD_PARTY_NOTICES.txt")
errors = [f"{p} is missing" for p in (license_txt, notices_txt) if not os.path.isfile(p)]
if errors:
    sys.exit("\n".join(f"::error::{e}" for e in errors))


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


if read(license_txt).split() != read(os.path.join(ROOT, "LICENSE")).split():
    errors.append("LICENSE.txt differs from the repository's LICENSE")

# sections look like: a line of 72 '=', the title, another line of 72 '='
pieces = re.split(r"^={72}$", read(notices_txt), flags=re.M)
titles = [p.strip().splitlines()[0] for p in pieces[1::2] if p.strip()]
bodies = pieces[2::2]
for want in REQUIRED:
    if not any(t.startswith(want) for t in titles):
        errors.append(f"no section for {want.strip()}")
if sys.platform.startswith("linux") and not any("(Linux system package)" in t for t in titles):
    errors.append("no Linux system packages are listed")
for title, body in zip(titles, bodies):
    if NOT_FOUND in body:
        errors.append(f"license text not found for: {title}")

print(f"{notices_txt}: {os.path.getsize(notices_txt)} bytes, {len(titles)} sections")
for t in titles:
    print("  " + t)
for e in errors:
    print(f"::error::{e}")
sys.exit(1 if errors else 0)
