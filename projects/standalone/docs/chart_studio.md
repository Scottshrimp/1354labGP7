# Rhythm Chart Studio v1.3 — WAV format playback correction

The accelerated/pitch-shifted playback could result from passing headerless
PCM bytes directly to pygame Sound(buffer=...). This release always feeds a
proper WAV stream with explicit 44100 Hz, signed 16-bit, stereo format and
requests exactly the matching pygame mixer settings (with no allowed changes).

All note-editing controls from v1.2 remain unchanged.

Run from the repository root: python src/chart_studio.py
Requirements: pygame, FFmpeg installed.

After importing AAC, test playback at 0:10 and 1:00. If playback remains
incorrect, share the actual audio device/mixer info and traceback.

## Standalone MEGALOVANIA workflow

Run from the repository root:

```sh
python src/chart_studio.py
```

Open `music/megalovania/chart.json`.
Import `source.mid` from the same folder to preview the converted lead; MIDI
preview needs pygame and the `src/tools/` directory, but does not need FFmpeg.
The temporary WAV is removed when the studio closes. It approximates the board's
melody; the hardware uses a different tone generator.

After saving, run `python src/tools/build_song.py`, then reflash the complete
`src/deploy/main.py`. Leave at least 1000 ms between cues for gentle mode.
