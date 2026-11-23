#!/usr/bin/env python3
"""Build the static Web Serial console and its matching public demo firmware."""

from array import array
import hashlib
import json
import math
import shutil
import sys
import wave

from build import ROOT, assembled_source, compile_deployment, pack_song_assets, standalone_builder

WEB = ROOT / "web"
DIST = ROOT / "dist"
SONGS = ROOT.parent / "pc-integrated" / "songs"
TITLE = "STARTER BEAT"
DIRECTIONS = ("UP", "RIGHT", "DOWN", "LEFT")
LANES = (0, 1, 2, 0, 1, 3, 3, 2)
PITCHES = (48, 55, 60, 55, 50, 57, 62, 57, 46, 53, 58, 53, 48, 55, 63, 60)
DURATION = 25_000
BEATS = [(1000 + i * 500, pitch) for i, pitch in enumerate((PITCHES * 3)[:46])]


def library():
    """PC songs that have browser audio prepared by tools/web_audio.py."""
    songs = []
    for meta_path in sorted(SONGS.glob("*/song.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        if not meta.get("web_audio"):
            continue
        chart = json.loads((meta_path.parent / meta["chart"]).read_text(encoding="utf-8-sig"))
        duration = int(chart.get("duration_ms", meta["duration_ms"]))
        notes = sorted({(int(n["time_ms"]), DIRECTIONS.index(n["direction"].upper())) for n in chart["notes"]})
        if not notes or not 0 < duration <= 3_600_000 or any(not 0 <= t < duration for t, _ in notes):
            raise ValueError(f"Invalid chart for {meta_path.parent.name}")
        # Same title rules as pc_host.py so both hosts list songs identically.
        title = "".join(c for c in meta["title"].upper() if c.isascii() and (c.isalnum() or c in " -_"))[:18]
        songs.append({
            "title": title or "SONG",
            "duration": duration,
            "notes": [list(note) for note in notes],
            "audio": "/media/" + meta["web_audio"],
        })
    return songs


def digest(*paths):
    hasher = hashlib.sha256()
    for path in paths:
        hasher.update(path.read_bytes())
    return hasher.hexdigest()[:10]


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f"Expected exactly one {before!r} while building the site")
    return text.replace(before, after)


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
    # Cloudflare caches .css/.js at the edge and overrides their Cache-Control,
    # so each release references them by a content hash to force fresh copies.
    for filename in ("app.mjs", "rh1.mjs", "match.mjs"):
        shutil.copyfile(WEB / "browser" / filename, browser / filename)
    app_version = digest(*(browser / name for name in ("app.mjs", "rh1.mjs", "match.mjs")))
    console = replace_once(
        (WEB / "console.js").read_text(encoding="utf-8"),
        '"./browser/app.mjs"', f'"./browser/app.mjs?v={app_version}"',
    )
    (DIST / "console.js").write_text(console, encoding="utf-8")
    shutil.copyfile(WEB / "style.css", DIST / "style.css")
    assets = {
        'href="/style.css"': f'href="/style.css?v={digest(DIST / "style.css")}"',
        'src="/console.js"': f'src="/console.js?v={digest(DIST / "console.js")}"',
    }

    page = replace_once(
        (WEB / "index.html").read_text(encoding="utf-8"),
        "    <!-- Browser host setup -->", (WEB / "browser/setup.html").read_text(encoding="utf-8").rstrip(),
    )
    tutorial = (WEB / "tutorial/index.html").read_text(encoding="utf-8")
    for before, after in assets.items():
        page = replace_once(page, before, after)
        if before in tutorial:
            tutorial = replace_once(tutorial, before, after)
    (DIST / "index.html").write_text(page, encoding="utf-8")
    (DIST / "tutorial").mkdir(exist_ok=True)
    (DIST / "tutorial/index.html").write_text(tutorial, encoding="utf-8")

    notes = [[stamp, LANES[index % len(LANES)]] for index, (stamp, _) in enumerate(BEATS)]
    (browser / "starter-beat.json").write_text(
        json.dumps({"title": TITLE, "duration": DURATION, "notes": notes}) + "\n", encoding="utf-8"
    )
    write_audio(browser / "starter-beat.wav")
    catalog = [{"title": TITLE, "duration": DURATION, "notes": notes, "audio": "starter-beat.wav"}, *library()]
    (browser / "songs.json").write_text(json.dumps(catalog, separators=(",", ":")) + "\n", encoding="utf-8")

    song = {
        "title": TITLE,
        "duration_ms": DURATION,
        "melody": [(stamp, 290, pitch) for stamp, pitch in BEATS],
        "notes": [{"time_ms": stamp, "direction": DIRECTIONS[lane]} for stamp, lane in notes[::2]],
    }
    assets = pack_song_assets([song], standalone_builder())
    firmware = compile_deployment(assembled_source(assets))
    (DIST / "main.py").write_text(firmware, encoding="utf-8")
    print(f"Static site: {DIST} ({len(catalog)} songs: {', '.join(song['title'] for song in catalog)})")
    print(f"Flash in Python Editor: {DIST / 'main.py'} ({len(firmware.encode())} bytes)")


if __name__ == "__main__":
    build()
