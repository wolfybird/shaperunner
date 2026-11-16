"""Checks that every file naming the current version agrees, and that a
version tag matches APP_VERSION. The build workflow runs it on every pull
request and tag; run it by hand before tagging:

    python .github/check_versions.py v10.4
"""
import os
import re
import subprocess
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
errors = []

tracked = subprocess.run(["git", "ls-files", "shapes_v*.py"], capture_output=True,
                         text=True, check=True).stdout.split()
if len(tracked) != 1:
    sys.exit(f"::error::expected exactly one tracked shapes_v*.py, found {tracked or 'none'}")
script = tracked[0]
with open(script, encoding="utf-8") as f:
    m = re.search(r'^APP_VERSION = "([^"]+)"', f.read(), re.M)
version = m.group(1) if m else None
if version is None:
    errors.append(f"{script} has no APP_VERSION line")

with open("ShapeRunner.spec", encoding="utf-8") as f:
    spec = f.read()
for name, want in (("SCRIPT", script), ("VERSION", version)):
    m = re.search(rf"^{name} = '([^']*)'", spec, re.M)
    if not m or m.group(1) != want:
        errors.append(f"ShapeRunner.spec has {name} = {m.group(1) if m else None!r}, "
                      f"expected {want!r}")

with open("pyproject.toml", encoding="utf-8") as f:
    named = sorted(set(re.findall(r"shapes_v[\w-]+\.py", f.read())))
if named != [script]:
    errors.append(f"pyproject.toml names {named}, expected only {script!r}")

tag = sys.argv[1] if len(sys.argv) > 1 else None
if tag is None and os.environ.get("GITHUB_REF_TYPE") == "tag":
    tag = os.environ.get("GITHUB_REF_NAME")
if tag and tag != f"v{version}":
    errors.append(f"tag {tag} doesn't match APP_VERSION {version!r} (expected v{version}). "
                  "To rebuild a version without a new tag, run Build apps by hand.")

for e in errors:
    print(f"::error::{e}")
if errors:
    sys.exit(1)
print(f"ok: {script}, version {version}" + (f", tag {tag}" if tag else ""))
