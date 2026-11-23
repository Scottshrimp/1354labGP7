#!/usr/bin/env python3
"""Build the static Web Serial console and its matching public demo firmware."""

from array import array
import json
import math
import shutil
import sys
import wave

from build import ROOT, assembled_source, compile_deployment, pack_song_assets, standalone_builder

WEB = ROOT / "web"
DIST = ROOT / "dist"
TITLE = "STARTER BEAT"
DIRECTIONS = ("UP", "RIGHT", "DOWN", "LEFT")
LANES = (0, 1, 2, 0, 1, 3, 3, 2)
PITCHES = (48, 55, 60, 55, 50, 57, 62, 57, 46, 53, 58, 53, 48, 55, 63, 60)
DURATION = 25_000
BEATS = [(1000 + i * 500, pitch) for i, pitch in enumerate((PITCHES * 3)[:46])]


def write_audio(path):
    rate = 44100
    samples = array("h", [0]) * (rate * DURATION // 1000)
    for index, (stamp, pitch) in enumerate(BEATS):
        offset = stamp * rate // 1000
        frequency = 440 * 2 ** ((pitch - 69) / 12)
        for frame in range(rate // 3):
            time = frame / rate
            pluck = math.sin(math.tau * frequency * time) * math.exp(-9 * time)
            click = math.sin(math.tau * (120 * time - 130 * time * time)) * math.exp(-37 * time)
            gain = min(1, frame / 64, (rate // 3 - frame - 1) / 64)
            samples[offset + frame] = round(gain * (8500 * pluck + (7300 if index % 4 == 0 else 4500) * click))
    if sys.byteorder != "little":
        samples.byteswap()
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        stream.writeframes(samples.tobytes())


def build():
    browser = DIST / "browser"
    browser.mkdir(parents=True, exist_ok=True)
    (DIST / "index.html").write_text(
        (WEB / "index.html").read_text(encoding="utf-8").replace(
            "    <!-- Browser host setup -->", (WEB / "browser/setup.html").read_text(encoding="utf-8").rstrip()
        ),
        encoding="utf-8",
    )
    for filename in ("style.css", "console.js"):
        shutil.copyfile(WEB / filename, DIST / filename)
    (DIST / "tutorial").mkdir(exist_ok=True)
    shutil.copyfile(WEB / "tutorial/index.html", DIST / "tutorial/index.html")
    for filename in ("app.mjs", "rh1.mjs", "match.mjs"):
        shutil.copyfile(WEB / "browser" / filename, browser / filename)

    notes = [[stamp, LANES[index % len(LANES)]] for index, (stamp, _) in enumerate(BEATS)]
    (browser / "starter-beat.json").write_text(
        json.dumps({"title": TITLE, "duration": DURATION, "notes": notes}) + "\n", encoding="utf-8"
    )
    write_audio(browser / "starter-beat.wav")

    song = {
        "title": TITLE,
        "duration_ms": DURATION,
        "melody": [(stamp, 290, pitch) for stamp, pitch in BEATS],
        "notes": [{"time_ms": stamp, "direction": DIRECTIONS[lane]} for stamp, lane in notes[::2]],
    }
    assets = pack_song_assets([song], standalone_builder())
    firmware = compile_deployment(assembled_source(assets))
    (DIST / "main.py").write_text(firmware, encoding="utf-8")
    print(f"Static site: {DIST}")
    print(f"Flash in Python Editor: {DIST / 'main.py'} ({len(firmware.encode())} bytes)")


if __name__ == "__main__":
    build()
