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
import sys
from importlib import metadata

APP = 'ShapeRunner'
SCRIPT = 'shapes_v10-3.py'
VERSION = '10.3'
SOURCE_URL = 'https://github.com/wolfybird/shaperunner'

# Python packages bundled in the app. Their own license files are read from
# this machine's installed copies, so the notices match each OS's build.
# pygame-ce's wheels carry no license files: licenses/pygame-ce has them,
# taken from its source at the matching version.
BUNDLED_PACKAGES = ['numpy', 'pygame-ce', 'sounddevice', 'cffi', 'pycparser']
PYGAME_CE_LICENSES_FROM = '2.5.8'       # see licenses/README.md


def read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def third_party_notices():
    rule = '=' * 72
    parts = [
        f'{APP} {VERSION} includes the software listed below. Each part is under\n'
        'its own license, given here in full.\n\n'
        f'{APP} itself is under the GNU GPL, version 3 or later (LICENSE.txt).\n'
        f'Source: {SOURCE_URL}\n'
    ]

    def add(title, text):
        parts.append(f'\n{rule}\n{title}\n{rule}\n\n{text.strip()}\n')

    py = 'python%d.%d' % sys.version_info[:2]
    for path in (os.path.join(sys.base_prefix, 'LICENSE.txt'),
                 os.path.join(sys.base_prefix, 'lib', py, 'LICENSE.txt')):
        if os.path.isfile(path):
            add(f'Python {platform.python_version()}', read(path))
            break
    else:
        raise SystemExit("Python's LICENSE.txt was not found")
    # Tcl/Tk come with Python's tkinter; not every Python's LICENSE.txt has them
    add('Tcl (the settings panel)', read(os.path.join(SPECPATH, 'licenses', 'tcl.txt')))
    add('Tk (the settings panel)', read(os.path.join(SPECPATH, 'licenses', 'tk.txt')))

    for name in BUNDLED_PACKAGES:
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            print(f'WARNING: {name} is not installed, so it is not in the notices')
            continue
        if name == 'pygame-ce':
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
        for path in chosen:
            add(f'{name} {dist.version}: {path.split(".dist-info/licenses/")[-1]}',
                (dist.locate_file(path)).read_text(encoding='utf-8'))

    add('PortAudio (audio input, used through sounddevice)',
        read(os.path.join(SPECPATH, 'licenses', 'portaudio.txt')))
    debian = '/usr/share/doc/libportaudio2/copyright'   # the Linux build's copy
    if os.path.isfile(debian):
        add('libportaudio2 (Linux package)', read(debian))
    return ''.join(parts)


notices_dir = os.path.join(SPECPATH, 'build', 'notices')
os.makedirs(notices_dir, exist_ok=True)
NOTICES = os.path.join(notices_dir, 'THIRD_PARTY_NOTICES.txt')
LICENSE = os.path.join(notices_dir, 'LICENSE.txt')
with open(NOTICES, 'w', encoding='utf-8', newline='\n') as f:
    f.write(third_party_notices())
shutil.copyfile(os.path.join(SPECPATH, 'LICENSE'), LICENSE)


a = Analysis(
    [SCRIPT],
    pathex=[],
    binaries=[],
    # macOS: data files go in Contents/Resources, inside the signed bundle
    datas=[(NOTICES, '.'), (LICENSE, '.')] if sys.platform == 'darwin' else [],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)


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
