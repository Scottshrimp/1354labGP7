#!/usr/bin/env python3
"""RH1 PC host. Audio is prepared before opening serial; one loop owns the link."""
import argparse
from collections import deque
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import time

from protocol import LineFramer, encode_line

ROOT = Path(__file__).resolve().parent
DEFAULT_SONGS = ROOT.parent / "pc-integrated" / "songs"
DIRECTIONS = {"UP": 0, "RIGHT": 1, "DOWN": 2, "LEFT": 3}
LEASE_SECONDS = 2.5


class ConnectionLost(RuntimeError):
    pass


def load_library(directory):
    """Validate and convert the whole catalog before advertising host readiness."""
    songs = []
    for path in sorted(Path(directory).glob("*/song.json")):
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        audio = path.parent / doc["audio"]
        if not audio.is_file():
            print("Skipping missing audio:", audio, flush=True)
            continue
        chart = json.loads((path.parent / doc["chart"]).read_text(encoding="utf-8-sig"))
        duration = int(chart.get("duration_ms", doc["duration_ms"]))
        notes = sorted(
            (int(n["time_ms"]), DIRECTIONS[n["direction"].upper()])
            for n in chart["notes"]
        )
        if not notes or len(notes) > 10000 or not 0 < duration <= 3600000:
            raise ValueError("Invalid chart size or duration: " + str(path))
        if any(not 0 <= t < duration for t, _ in notes):
            raise ValueError("Chart note outside song: " + str(path))
        title = (
            "".join(
                c
                for c in doc["title"].upper()
                if c.isascii() and (c.isalnum() or c in " -_")
            )[:18]
            or "SONG"
        )
        wav = path.parent / "cache.wav"
        if not wav.is_file() or wav.stat().st_mtime < audio.stat().st_mtime:
            if not shutil.which("ffmpeg"):
                raise RuntimeError("FFmpeg is required to prepare " + str(audio))
            print("Preparing audio:", title, flush=True)
            temporary = path.parent / "cache.preparing.wav"
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-v",
                        "error",
                        "-y",
                        "-i",
                        str(audio),
                        "-ar",
                        "44100",
                        "-ac",
                        "2",
                        str(temporary),
                    ],
                    check=True,
                )
                temporary.replace(wav)
            finally:
                temporary.unlink(missing_ok=True)
        songs.append({"title": title, "duration": duration, "notes": notes, "wav": wav})
        if len(songs) == 12:
            break
    if not songs:
        raise ValueError("No playable songs. Add audio to " + str(directory))
    return songs


class PygameAudio:
    def __init__(self):
        import pygame

        pygame.mixer.init(44100, -16, 2, 512)
        self.mixer = pygame.mixer
        self.music = pygame.mixer.music

    def load(self, path):
        self.music.load(str(path))

    def play(self):
        self.music.play()

    def stop(self):
        self.music.stop()

    def pause(self):
        self.music.pause()

    def resume(self):
        self.music.unpause()

    def close(self):
        self.mixer.quit()


class HostSession:
    """Deterministic protocol/audio controller; caller owns serial and the clock."""

    def __init__(self, songs, audio, offset_ms=0, nonce=None, log=print):
        if not -1000 <= offset_ms <= 1000:
            raise ValueError("Audio offset must be between -1000 and 1000 ms")
        self.songs, self.audio = songs, audio
        self.offset = offset_ms / 1000
        self.host_nonce = nonce or secrets.token_hex(4)
        self.log = log
        self.framer = LineFramer()
        self.session = None
        self.challenge = None
        self.seq = 0
        self.pending = deque()
        self.inflight = None
        self.sent_at = 0.0
        self.last_rx = None
        self.last_tx = -1.0
        self.attach_at = -1.0
        self.round = None
        self.song = None
        self.cursor = 0
        self.end_queued = False
        self.state = "CONNECTING"
        self.audio_at = None
        self.pause_at = None
        self.playing = False
        self.event_seq = 0

    def stop_round(self):
        self.audio.stop()
        self.audio_at = self.pause_at = None
        self.playing = False
        self.round = self.song = None
        self.pending.clear()
        self.state = "MENU"

    def close(self):
        self.stop_round()

    def queue(self, command, *values):
        self.pending.append((command,) + tuple(values))

    def add_notes(self, start, capacity):
        if self.song is None or self.end_queued:
            return
        # Ignore repeated NEED while a batch is still queued/in flight.
        if any(item[0] == "N" for item in self.pending):
            return
        if self.inflight is not None and self.inflight[0] == "N":
            return
        if start > self.cursor:
            raise ConnectionLost("Device requested an unknown chart position")
        count = min(12, max(0, capacity))
        for index in range(
            self.cursor, min(self.cursor + count, len(self.song["notes"]))
        ):
            stamp, direction = self.song["notes"][index]
            self.queue("N", self.round, index, stamp, direction)
            self.cursor = index + 1
        if self.cursor == len(self.song["notes"]):
            self.queue("END", self.round)
            self.end_queued = True

    def select(self, round_id, index):
        self.stop_round()
        self.round = round_id
        self.song = self.songs[index]
        self.cursor = 0
        self.end_queued = False
        self.audio.load(self.song["wav"])
        self.state = "READY"
        self.queue("BEGIN", round_id, self.song["duration"], len(self.song["notes"]))
        # First batch is 24 cues; later refills are capped at 12.
        for index, (stamp, direction) in enumerate(self.song["notes"][:24]):
            self.queue("N", round_id, index, stamp, direction)
            self.cursor = index + 1
        if self.cursor == len(self.song["notes"]):
            self.queue("END", round_id)
            self.end_queued = True
        self.queue("ARM", round_id)
        self.log("Ready: " + self.song["title"])

    def event(self, fields, now):
        kind = fields[0]
        if kind == "SELECT" and len(fields) == 3:
            round_id, index = int(fields[1]), int(fields[2])
            if not 0 <= round_id < 65536 or not 0 <= index < len(self.songs):
                raise ValueError("Invalid selection")
            try:
                self.select(round_id, index)
            except Exception as error:
                self.log("Audio loading failed: " + str(error))
                self.stop_round()
                self.queue("ERROR", round_id)
            return
        if len(fields) < 2 or int(fields[1]) != self.round:
            return
        if kind == "START" and self.song is not None and self.state == "READY":
            self.queue("SYNC", self.round)
            self.state = "SYNCING"
        elif kind == "SYNCED" and self.state == "SYNCING":
            self.audio_at = now + 2.7 + self.offset
            self.state = "PLAY"
            self.log("Countdown started")
        elif kind == "NEED" and len(fields) == 4:
            start, capacity = int(fields[2]), int(fields[3])
            if not 0 <= capacity <= 44 or start < 0:
                raise ValueError("Invalid refill")
            self.add_notes(start, capacity)
        elif kind == "PAUSE" and self.state == "PLAY":
            self.audio.pause()
            self.pause_at = now
            self.state = "PAUSED"
        elif kind == "RESUME" and self.state == "PAUSED":
            if self.audio_at is not None:
                self.audio_at += now - self.pause_at
            elif self.playing:
                self.audio.resume()
            self.pause_at = None
            self.state = "PLAY"
        elif kind in ("STOP", "DONE", "STARVED"):
            if kind == "DONE":
                self.log("Result: score " + fields[2] + ", miss " + fields[3])
            if kind == "STARVED":
                self.log("Chart delivery timed out; round cancelled")
            self.stop_round()

    def feed(self, data, now):
        for line in self.framer.feed(data):
            fields = line.split(",")
            if len(fields) == 3 and fields[:2] == ["RH1", "HELLO"]:
                challenge = fields[2]
                if len(challenge) != 8 or any(
                    c not in "0123456789abcdef" for c in challenge
                ):
                    continue
                if self.session is not None:
                    raise ConnectionLost("Device restarted or expired the connection")
                if challenge != self.challenge:
                    self.challenge = challenge
                    self.attach_at = -1.0
                continue
            if fields == ["RH1", "ACCEPT", (self.challenge or "") + self.host_nonce]:
                if self.session is None:
                    self.session = fields[2]
                    self.last_rx = now
                    self.state = "CATALOG"
                    self.queue("CATBEGIN", len(self.songs))
                    for index, song in enumerate(self.songs):
                        self.queue("CAT", index, song["title"])
                    self.queue("READY")
                    self.log("Connected; switching is deferred until the device menu")
                continue
            if len(fields) < 4 or fields[:2] != ["RH1", self.session]:
                continue
            try:
                if fields[2] == "A" and len(fields) == 5 and self.inflight is not None:
                    if int(fields[3]) != self.seq:
                        continue
                    if fields[4] != "OK":
                        raise ConnectionLost("Device rejected " + self.inflight[0])
                    if self.inflight[0] == "READY":
                        self.state = "MENU"
                    self.inflight = None
                    self.seq = (self.seq + 1) % 65536
                    self.last_rx = now
                elif fields[2] == "E" and len(fields) >= 5:
                    event_seq = int(fields[3])
                    if event_seq == self.event_seq:
                        self.event(fields[4:], now)
                        self.event_seq = (self.event_seq + 1) % 65536
                    elif event_seq != (self.event_seq - 1) % 65536:
                        continue
                    # Acknowledge only after handling, including STOP which clears work.
                    ack = ("EA", event_seq)
                    if ack not in self.pending:
                        self.pending.appendleft(ack)
                    self.last_rx = now
            except (ValueError, IndexError) as error:
                raise ConnectionLost("Invalid device message: " + line) from error

    def tick(self, now):
        """Return at most one <=61 byte frame; no concurrent heartbeat writes."""
        if self.session is None:
            if self.challenge and now - self.attach_at >= 0.8:
                self.attach_at = now
                return encode_line("RH1", "ATTACH", self.challenge, self.host_nonce)
            return None
        if now - self.last_rx >= LEASE_SECONDS:
            self.stop_round()
            raise ConnectionLost("Device heartbeat timed out")
        # Link liveness is checked before audio can start.
        if self.audio_at is not None and self.state == "PLAY" and now >= self.audio_at:
            self.audio.play()
            self.audio_at = None
            self.playing = True
            self.log("Audio playback started")
        if self.inflight is not None:
            if now - self.sent_at < 0.8:
                return None
        else:
            if not self.pending and now - self.last_tx < 0.5:
                return None
            self.inflight = self.pending.popleft() if self.pending else ("HB",)
        self.sent_at = self.last_tx = now
        return encode_line("RH1", self.session, self.seq, *self.inflight)


def choose_port(requested=None):
    from serial.tools import list_ports

    if requested:
        return requested
    ports = [
        p.device
        for p in list_ports.comports()
        if p.vid == 0x0D28
        or "micro:bit" in (p.description or "").lower()
        or "microbit" in (p.description or "").lower()
    ]
    if len(ports) > 1:
        raise ValueError("Multiple micro:bits found; select one with --port")
    return ports[0] if ports else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port", help="Serial device; auto-detects a single micro:bit by default"
    )
    parser.add_argument("--songs", type=Path, default=DEFAULT_SONGS)
    parser.add_argument(
        "--offset-ms",
        type=int,
        default=0,
        help="Positive delays PC audio; range -1000 to 1000",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Prepare/validate songs without opening serial or audio",
    )
    args = parser.parse_args()
    if not -1000 <= args.offset_ms <= 1000:
        parser.error("--offset-ms must be between -1000 and 1000")
    songs = load_library(args.songs)
    print("Prepared", len(songs), "songs", flush=True)
    if args.check:
        return
    import serial

    audio = PygameAudio()
    host = None
    try:
        print(
            "Waiting for micro:bit. Close the Python Editor serial connection.",
            flush=True,
        )
        while True:
            port = choose_port(args.port)
            if port is None:
                time.sleep(1)
                continue
            try:
                with serial.Serial(port, 115200, timeout=0, write_timeout=0.3) as link:
                    print("Opening", port, flush=True)
                    host = HostSession(
                        songs,
                        audio,
                        args.offset_ms,
                        log=lambda message: print(message, flush=True),
                    )
                    hello_deadline = time.monotonic() + 8
                    while True:
                        now = time.monotonic()
                        data = link.read(min(4096, link.in_waiting))
                        if data:
                            host.feed(data, now)
                        if host.session is None and now > hello_deadline:
                            raise ConnectionLost(
                                "No RH1 firmware response; check the flashed program"
                            )
                        frame = host.tick(now)
                        if frame is not None:
                            link.write(frame)
                        time.sleep(0.002)
            except (serial.SerialException, OSError, ConnectionLost) as error:
                if host:
                    host.close()
                print(str(error) + "; retrying in 1 second", flush=True)
                time.sleep(1)
            finally:
                if host:
                    host.close()
                host = None
    finally:
        if host:
            host.close()
        audio.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nPC host stopped")
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
