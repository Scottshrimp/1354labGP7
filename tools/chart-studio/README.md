# Rhythm Chart Studio v1.3 — WAV format playback correction

The accelerated/pitch-shifted playback could result from passing headerless
PCM bytes directly to pygame Sound(buffer=...). This release always feeds a
proper WAV stream with explicit 44100 Hz, signed 16-bit, stereo format and
requests exactly the matching pygame mixer settings (with no allowed changes).

All note-editing controls from v1.2 remain unchanged.

Run from the repository root:

```sh
python -m pip install -r tools/chart-studio/requirements.txt
python tools/chart-studio/chart_studio.py
```

Requires Python 3.10+, Tkinter, pygame, and FFmpeg on PATH for audio imports.
Open a chart from `projects/pc-integrated/songs/<song-id>/chart.json`, then
import its matching local audio file. Audio files are excluded from Git.

For the standalone project's MIDI preview, use
`python projects/standalone/src/chart_studio.py` instead; that version includes
the shared MIDI converter integration.

After importing AAC, test playback at 0:10 and 1:00. If playback remains
incorrect, share the actual audio device/mixer info and traceback.
