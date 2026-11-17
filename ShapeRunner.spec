# -*- mode: python ; coding: utf-8 -*-
# Builds the app for the OS it runs on: pyinstaller ShapeRunner.spec
#   Windows  dist/ShapeRunner/ShapeRunner.exe (window) and
#            ShapeRunner-terminal.exe (terminal mode, opens a console)
#   macOS    dist/ShapeRunner.app
#   Linux    dist/ShapeRunner/ShapeRunner
# Each app also carries LICENSE.txt (ShapeRunner's GPL) and
# THIRD_PARTY_NOTICES.txt (the licenses of everything bundled with it):
# next to the program on Windows and Linux, in Contents/Resources on macOS.
import os
import platform
import shutil
import stat
import subprocess
import sys
import sysconfig
from importlib import metadata

APP = 'ShapeRunner'
SCRIPT = 'shapes_v10-5.py'
VERSION = '10.5'
SOURCE_URL = 'https://github.com/wolfybird/shaperunner'

# Python packages bundled in the app. Their own license files are read from
# this machine's installed copies, so the notices match each OS's build.
# pygame-ce's wheels carry no license files: licenses/pygame-ce has them,
# taken from its source at PYGAME_CE_LICENSES_FROM. A different minor
# version stops the build until they are refreshed (see licenses/README.md).
BUNDLED_PACKAGES = ['numpy', 'pygame-ce', 'sounddevice', 'cffi', 'pycparser']
PYGAME_CE_LICENSES_FROM = '2.5.8'
# written into the notices when a license can't be found; CI fails on it
NOT_FOUND = 'LICENSE TEXT NOT FOUND ON THE BUILD MACHINE'


def read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def python_license():
    """Python's LICENSE.txt: next to python.exe on Windows, in the standard
    library folder elsewhere (lib, lib64 or a free-threaded pythonX.Yt)."""
    for folder in (sys.base_prefix, sysconfig.get_path('stdlib')):
        path = os.path.join(folder, 'LICENSE.txt')
        if os.path.isfile(path):
            return read(path)
    raise SystemExit("Python's LICENSE.txt was not found")


def linux_system_libraries(binaries):
    """The system libraries PyInstaller bundled on Linux, grouped by the
    Debian package that installed them: ({package: [files]}, [unclaimed])."""
    paths = {}
    for dest, src, _ in binaries:
        if (src.startswith(('/lib/', '/lib64/', '/usr/lib/', '/usr/lib64/'))
                and 'site-packages' not in src):
            paths[src] = os.path.basename(dest)
    if not paths or not shutil.which('dpkg'):
        return {}, sorted(paths.values())
    # dpkg knows each file by the path its package installed; with a merged
    # /usr that may be /lib/... or /usr/lib/..., and links point elsewhere
    asked = {}
    for p in paths:
        for cand in {p, os.path.realpath(p)}:
            asked[cand] = p
            asked[cand[4:] if cand.startswith('/usr/') else '/usr' + cand] = p
    out = subprocess.run(['dpkg', '-S', *asked], capture_output=True, text=True).stdout
    packages, claimed = {}, set()
    for line in out.splitlines():
        pkg, sep, path = line.partition(': ')
        p = asked.get(path.strip())
        if sep and p and ',' not in pkg and 'diversion' not in pkg:
            packages.setdefault(pkg.split(':')[0], set()).add(paths[p])
            claimed.add(p)
    unclaimed = sorted(paths[p] for p in paths if p not in claimed)
    return {k: sorted(v) for k, v in sorted(packages.items())}, unclaimed


def third_party_notices(binaries):
    rule = '=' * 72
    parts = [
        f'{APP} {VERSION} includes the software listed below. Each part is under\n'
        'its own license, given here in full.\n\n'
        f'{APP} itself is under the GNU GPL, version 3 or later (LICENSE.txt).\n'
        f'Source: {SOURCE_URL}\n'
    ]

    def add(title, text):
        parts.append(f'\n{rule}\n{title}\n{rule}\n\n{text.strip()}\n')

    add(f'Python {platform.python_version()}', python_license())
    # Tcl/Tk come with Python's tkinter; not every Python's LICENSE.txt has them
    add('Tcl (the settings panel)', read(os.path.join(SPECPATH, 'licenses', 'tcl.txt')))
    add('Tk (the settings panel)', read(os.path.join(SPECPATH, 'licenses', 'tk.txt')))

    for name in BUNDLED_PACKAGES:
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            raise SystemExit(f'{name} is not installed, so its license is unknown; '
                             'install requirements.txt (plain pygame is not supported)')
        if name == 'pygame-ce':
            if dist.version.split('.')[:2] != PYGAME_CE_LICENSES_FROM.split('.')[:2]:
                raise SystemExit(f'licenses/pygame-ce is from pygame-ce {PYGAME_CE_LICENSES_FROM} '
                                 f'but this build uses {dist.version}: refresh it, see '
                                 'licenses/README.md')
            if dist.version != PYGAME_CE_LICENSES_FROM:
                print(f'WARNING: licenses/pygame-ce is from pygame-ce '
                      f'{PYGAME_CE_LICENSES_FROM}, this build uses {dist.version}')
            vendored = os.path.join(SPECPATH, 'licenses', 'pygame-ce')
            add(f'pygame-ce {dist.version} (the window), LGPL-2.1-or-later\n'
                f'Source: https://github.com/pygame-community/pygame-ce/tree/{dist.version}',
                read(os.path.join(vendored, 'LGPL.txt')))
            for fn in sorted(os.listdir(vendored)):
                if fn.startswith('LICENSE.'):
                    add(f'pygame-ce includes {fn[len("LICENSE."):-len(".txt")]}',
                        read(os.path.join(vendored, fn)))
            continue
        files = [str(f).replace('\\', '/') for f in dist.files or []]
        # the license files the package declares; older packages only have
        # license-named files somewhere in their folders
        chosen = [p for p in files if '.dist-info/licenses/' in p] or [
            p for p in files
            if os.path.basename(p).upper().startswith(('LICENSE', 'COPYING'))]
        chosen += [p for p in files if p.endswith('portaudio-binaries/README.md')]
        if not chosen:
            add(f'{name} {dist.version}', NOT_FOUND)
        for path in chosen:
            add(f'{name} {dist.version}: {path.split(".dist-info/licenses/")[-1]}',
                read(dist.locate_file(path)))

    add('PortAudio (audio input, used through sounddevice)',
        read(os.path.join(SPECPATH, 'licenses', 'portaudio.txt')))

    if sys.platform.startswith('linux'):
        packages, unclaimed = linux_system_libraries(binaries)
        for pkg, libs in packages.items():
            copyright_file = f'/usr/share/doc/{pkg}/copyright'
            text = read(copyright_file) if os.path.isfile(copyright_file) else NOT_FOUND
            add(f'{pkg} (Linux system package): {", ".join(libs)}', text)
        if unclaimed:
            print(f'WARNING: no package found for {", ".join(unclaimed)}')
            add('Linux system libraries from no known package: ' + ', '.join(unclaimed),
                NOT_FOUND)
    return ''.join(parts)


a = Analysis(
    [SCRIPT],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# the notices list what Analysis found to bundle, so they come after it
notices_dir = os.path.join(SPECPATH, 'build', 'notices')
os.makedirs(notices_dir, exist_ok=True)
NOTICES = os.path.join(notices_dir, 'THIRD_PARTY_NOTICES.txt')
LICENSE = os.path.join(notices_dir, 'LICENSE.txt')
with open(NOTICES, 'w', encoding='utf-8', newline='\n') as f:
    f.write(third_party_notices(a.binaries))
shutil.copyfile(os.path.join(SPECPATH, 'LICENSE'), LICENSE)
if sys.platform == 'darwin':
    # data files go in Contents/Resources, inside the signed bundle
    a.datas += [('THIRD_PARTY_NOTICES.txt', NOTICES, 'DATA'),
                ('LICENSE.txt', LICENSE, 'DATA')]


def make_exe(name, console):
    return EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=console,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )


exes = [make_exe(APP, console=False)]
if sys.platform == 'win32':
    exes.append(make_exe(APP + '-terminal', console=True))

# Folders under OneDrive can turn read-only, and Windows won't delete a
# read-only folder, so COLLECT's removal of the previous build fails with
# "Access is denied". Clear the flag on the old build first.
for dirpath, _, filenames in os.walk(os.path.join(DISTPATH, APP)):
    for path in [dirpath] + [os.path.join(dirpath, f) for f in filenames]:
        os.chmod(path, os.stat(path).st_mode | stat.S_IWRITE)

coll = COLLECT(
    *exes,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name=APP + '.app',
        bundle_identifier='io.github.wolfybird.shaperunner',
        version=VERSION,
        info_plist={
            'CFBundleDisplayName': 'ShapeRunner',
            'NSHighResolutionCapable': True,
            'NSHumanReadableCopyright': 'Copyright (C) 2026 RFrank. GPL-3.0-or-later.',
            # without this macOS stops the app when audio mode opens the mic
            'NSMicrophoneUsageDescription':
                'Audio mode makes the shapes react to sound from your microphone.',
        },
    )
else:
    # next to the program, where people see them
    for path in (NOTICES, LICENSE):
        shutil.copy(path, os.path.join(DISTPATH, APP))
