# Licenses of bundled software

The ready-made apps include other open-source software. `ShapeRunner.spec`
collects their licenses into `THIRD_PARTY_NOTICES.txt` in each app. Most of
the texts come from the installed packages. This folder has the ones that
aren't installed with them:

- `pygame-ce/`: pygame-ce's wheels carry no license files, so these come
  from its source at version 2.5.8: `docs/LGPL.txt` and `docs/licenses/`
  from https://github.com/pygame-community/pygame-ce/tree/2.5.8/docs. When
  the apps are built with a newer pygame-ce, refresh these files and update
  `PYGAME_CE_LICENSES_FROM` in the spec (the build warns about a mismatch).
- `portaudio.txt`: PortAudio's `LICENSE.txt` at v19.7.0, from
  https://github.com/PortAudio/portaudio.
- `tcl.txt` and `tk.txt`: the `license.terms` of Tcl and Tk (8.6 branch),
  which come with Python's tkinter, from https://github.com/tcltk. Not every
  Python's own `LICENSE.txt` includes them.
