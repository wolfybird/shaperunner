#!/usr/bin/env python3
"""
Sets up ShapeRunner to run in the terminal.

It makes a private Python environment in the .venv folder (your other
Python programs are not touched), installs the packages the program needs
there, and creates a launcher you can double-click. Running it again is
safe: it reuses what is there and updates the packages.

The launcher runs "install.py --start", which starts the newest
shapes_v*.py in this folder, so after an update (a newer download or a
git pull) it runs the new version without setting up again. Run the setup
again to update the packages.

To undo it, delete the .venv folder and the launcher it made.

Start it with install_windows.bat, install_mac.command or install_linux.sh,
or run:  python3 install.py
"""

import os
import platform
import re
import stat
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(HERE, ".venv")
STEPS = 4
# launchers made before the program was renamed ShapeRunner (v10.1)
OLD_LAUNCHERS = ["Run ASCII 3D Shapes.bat", "Run ASCII 3D Shapes.command",
                 "run_ascii3dshapes.sh"]


def say(text=""):
    print(text, flush=True)


def step(n, text):
    say(f"\n[{n}/{STEPS}] {text}")


def stop(problem, *hints):
    say(f"\nSetup stopped: {problem}")
    for hint in hints:
        say(f"  {hint}")
    sys.exit(1)


def newest_script():
    """The highest-numbered shapes_v*.py (shapes_v10.py beats shapes_v9-7.py)."""
    best = None
    for name in os.listdir(HERE):
        m = re.fullmatch(r"shapes_v(\d+)(?:-(\d+))?(?:-(\d+))?\.py", name)
        if m:
            key = tuple(int(g or 0) for g in m.groups())
            if best is None or key > best[0]:
                best = (key, name)
    return best[1] if best else None


def venv_python():
    if os.name == "nt":
        return os.path.join(VENV, "Scripts", "python.exe")
    return os.path.join(VENV, "bin", "python")


def runs(cmd):
    return subprocess.run(cmd, cwd=HERE, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def start_newest(args):
    """What the launcher runs: the newest shapes_v*.py, with these args."""
    script = newest_script()
    if script is None:
        say("There is no shapes_v*.py file next to install.py.")
        return 1
    cmd = [sys.executable, os.path.join(HERE, script)] + args
    os.chdir(HERE)
    if os.name != "nt":
        os.execv(sys.executable, cmd)        # becomes the program
    proc = subprocess.Popen(cmd)
    while True:
        try:
            return proc.wait()
        except KeyboardInterrupt:            # Ctrl+C is the program's to handle
            continue


def audio_problem(py):
    """Why sounddevice doesn't load in the .venv, as ("", "") when it does,
    or (kind, detail) with kind "missing", "start" or "broken"."""
    r = subprocess.run([py, "-c", "import sounddevice"], cwd=HERE,
                       capture_output=True, text=True)
    if r.returncode == 0:
        return "", ""
    lines = r.stderr.strip().splitlines()
    last = lines[-1] if lines else f"exit code {r.returncode}"
    if "PortAudio library not found" in last:
        return "missing", last
    if "PortAudioError" in last:
        return "start", last
    return "broken", last


def pip_install(py, package):
    """Install or update one package; returns the error text, or ""."""
    r = subprocess.run([py, "-m", "pip", "install", "--upgrade", "--quiet",
                        "--disable-pip-version-check", package],
                       cwd=HERE, capture_output=True, text=True)
    if r.returncode == 0:
        return ""
    lines = (r.stderr or r.stdout).strip().splitlines()
    return "\n    ".join(lines[-4:]) or f"pip exited with code {r.returncode}"


def make_venv():
    py = venv_python()
    if os.path.exists(py) and runs([py, "-m", "pip", "--version"]):
        say("  Already there, reusing it.")
        return py
    try:
        import venv
        venv.EnvBuilder(with_pip=True, clear=os.path.exists(VENV)).create(VENV)
    except (Exception, SystemExit) as e:   # Debian's venv exits when pip is missing
        if isinstance(e, SystemExit):
            e = "Python's venv tool stopped, see its message above"
        hints = []
        if sys.platform.startswith("linux"):
            hints.append("Ubuntu, Debian and Mint need venv support installed first:")
            hints.append("  sudo apt install python3-venv")
            hints.append("then run this setup again.")
        stop(f"couldn't create the .venv folder ({e}).", *hints)
    if not os.path.exists(py):
        stop("the .venv folder was made but has no Python in it.",
             "Delete the .venv folder and run this setup again.")
    say("  Done.")
    return py


def write_launcher():
    """Create the double-click launcher for this OS; returns its name.
    It starts the newest version through install.py --start."""
    if os.name == "nt":
        name = "Run ShapeRunner.bat"
        text = ("@echo off\r\n"
                "cd /d \"%~dp0\"\r\n"
                "title ShapeRunner\r\n"
                "\".venv\\Scripts\\python.exe\" install.py --start --terminal\r\n"
                "if errorlevel 1 pause\r\n")
    else:
        name = ("Run ShapeRunner.command" if sys.platform == "darwin"
                else "run_shaperunner.sh")
        text = ("#!/bin/bash\n"
                "cd \"$(dirname \"$0\")\" || exit 1\n"
                "printf '\\e[8;55;180t'    # ask the terminal for a bigger window\n"
                ".venv/bin/python install.py --start --terminal\n")
    path = os.path.join(HERE, name)
    with open(path, "w", newline="") as f:
        f.write(text)
    if os.name != "nt":
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    for old in OLD_LAUNCHERS:
        try:
            os.remove(os.path.join(HERE, old))
        except OSError:
            pass
    return name


def main():
    say("ShapeRunner - terminal version setup")
    say("=" * 36)
    if sys.version_info < (3, 8):
        stop(f"this needs Python 3.8 or newer, and this one is {platform.python_version()}.",
             "Get a newer one at https://www.python.org/downloads/")
    script = newest_script()
    if script is None:
        stop("there is no shapes_v*.py file next to install.py.",
             "Keep install.py in the project folder and run it from there.")
    say(f"Python {platform.python_version()}, program {script}")

    step(1, "Making a private Python environment in .venv")
    py = make_venv()

    step(2, "Installing numpy (needed; this can take a minute)")
    err = pip_install(py, "numpy")
    if err:
        stop(f"numpy didn't install:\n    {err}",
             "Check your internet connection, then run this setup again.")
    say("  Done.")

    step(3, "Installing sounddevice (optional: makes shapes react to sound)")
    audio_note = ""
    err = pip_install(py, "sounddevice")
    if err:
        audio_note = "Audio mode is off: sounddevice didn't install."
        say(f"  Skipped. The program works without it.\n    {err}")
    else:
        kind, detail = audio_problem(py)
        if kind == "missing":
            audio_note = "Audio mode is off until PortAudio is installed."
            if sys.platform.startswith("linux"):
                audio_note += " On Ubuntu, Debian or Mint:  sudo apt install libportaudio2"
        elif kind == "start":
            audio_note = "Audio mode is off: PortAudio is installed but couldn't start."
            if sys.platform.startswith("linux"):
                audio_note += " Is a sound server (PipeWire or PulseAudio) running?"
        elif kind == "broken":
            audio_note = "Audio mode is off: sounddevice didn't load."
        if kind:
            say(f"  Installed, but it can't load yet. {audio_note}\n    {detail}")
        else:
            say("  Done.")

    step(4, "Creating the launcher")
    launcher = write_launcher()
    say(f"  Made \"{launcher}\". It always starts the newest version here.")

    say("\n" + "=" * 36)
    say("All set!")
    if os.name == "nt":
        say(f"To start: double-click \"{launcher}\" in this folder.")
    elif sys.platform == "darwin":
        say(f"To start: double-click \"{launcher}\" in this folder.")
        say("The first time, macOS may block it: right-click it, choose Open, then Open.")
    else:
        say(f"To start: run ./{launcher} in a terminal (or double-click it,")
        say("if your file manager allows running scripts).")
    say("In the program: m opens the menu, ? shows all keys, q quits.")
    if audio_note:
        say(audio_note)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--start"]:
        sys.exit(start_newest(sys.argv[2:]))
    main()
