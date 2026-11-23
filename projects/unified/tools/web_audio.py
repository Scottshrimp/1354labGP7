#!/usr/bin/env python3
"""Prepare browser audio for the PC song library (macOS).

Encodes each song's ``cache.wav`` (the exact PCM the Python host plays) to
AAC in an .m4a with afconvert. The encoder's priming is recorded in the file,
so Chrome decodes it sample-aligned with ``cache.wav`` and the existing charts
stay in sync. Output goes to ``projects/unified/media/<song-id>-<hash>.m4a``
(ignored by Git) and the name is stored as ``web_audio`` in ``song.json`` so
the web build can reference it. Content-hashed names are cached forever.

Upload new files to VPS3 before releasing a build that references them:

    rsync -av --ignore-existing projects/unified/media/ root@45.32.60.198:/srv/rhythmhit/media/
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SONGS = ROOT.parent / "pc-integrated" / "songs"
MEDIA = ROOT / "media"


def prepare(song_dir, force=False):
    meta_path = song_dir / "song.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    current = meta.get("web_audio")
    if current and (MEDIA / current).is_file() and not force:
        return current, False

    audio = song_dir / meta["audio"]
    wav = song_dir / "cache.wav"
    if not wav.is_file() or (audio.is_file() and wav.stat().st_mtime < audio.stat().st_mtime):
        raise SystemExit(
            f"{wav} is missing or older than {audio.name}; run "
            "`python3 projects/unified/pc_host.py --check` first to rebuild it."
        )

    MEDIA.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        encoded = Path(work) / "audio.m4a"
        subprocess.run(
            ["afconvert", "-f", "m4af", "-d", "aac", "-b", "192000", "-s", "0", str(wav), str(encoded)],
            check=True,
        )
        digest = hashlib.sha256(encoded.read_bytes()).hexdigest()[:10]
        name = f"{song_dir.name}-{digest}.m4a"
        shutil.copyfile(encoded, MEDIA / name)

    meta["web_audio"] = name
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return name, True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="re-encode songs that already have web audio")
    args = parser.parse_args()
    if not shutil.which("afconvert"):
        raise SystemExit("afconvert (macOS) is required.")
    for song_dir in sorted(path.parent for path in SONGS.glob("*/song.json")):
        name, fresh = prepare(song_dir, args.force)
        size = (MEDIA / name).stat().st_size / 1e6
        print(f"{'encoded' if fresh else 'kept   '} {name} ({size:.1f} MB)")


if __name__ == "__main__":
    main()
