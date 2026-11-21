#!/usr/bin/env python3
"""Two-player Rhythm Hit host with a local browser console."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
from threading import Event, Lock, Thread
import time

from pc_host import (
    DEFAULT_SONGS,
    ConnectionLost,
    HostSession,
    PygameAudio,
    find_ports,
    load_library,
)


PROBES = 4
MAX_CLOCK_RTT = 0.065
COUNTDOWN = 3.5
START_MARGIN = 2.25
TERMINAL = {"finished", "quit", "failed", "disconnected"}
WEB_DIR = Path(__file__).resolve().parent / "web"


class PlayerSession(HostSession):
    """One RH1 connection, with its own chart buffer and clock samples."""

    def __init__(self, songs, **kwargs):
        super().__init__(songs, audio=None, **kwargs)
        self.connected = True
        self.in_lobby = False
        self.status = "connecting"
        self.score = self.combo = self.miss = self.elapsed = 0
        self.probes = 0
        self.probe_sent_at = None
        self.sample = None
        self.scheduled = self.committed = False

    def announce(self):
        self.queue("DUO")

    def stop_round(self):
        self.disconnect()
        self.clear_round()

    def disconnect(self):
        self.connected = self.in_lobby = False
        if self.status not in TERMINAL:
            self.status = "disconnected"

    def begin(self, round_id, index):
        self.in_lobby = False
        self.status = "loading"
        self.score = self.combo = self.miss = self.elapsed = 0
        self.probes = 0
        self.probe_sent_at = None
        self.sample = None
        self.scheduled = self.committed = False
        self.prepare_chart(round_id, index, preload=40)

    def acknowledged(self, command):
        if command == "ARM" and self.status == "loading":
            self.status = "waiting"
        elif command == "AT":
            self.scheduled = True
        elif command == "GO":
            self.committed = True
        elif command == "CANCEL":
            self.round = self.song = None
            self.in_lobby = True
            self.status = "idle"

    def event(self, fields, now):
        kind = fields[0]
        if len(fields) < 2 or (self.round is not None and int(fields[1]) != self.round):
            return
        if kind == "LOBBY" and len(fields) == 2:
            self.in_lobby = True
            if self.round is None:
                self.status = "idle"
        elif self.song is None or self.status in TERMINAL:
            return
        elif kind == "START" and len(fields) == 2 and self.status == "waiting":
            self.status = "ready"
        elif kind == "NEED" and len(fields) == 4 and self.status == "playing":
            start, capacity = map(int, fields[2:])
            if not 0 <= capacity <= 44 or not 0 <= start <= self.cursor:
                raise ValueError("Invalid refill")
            self.add_notes(start, capacity)
        elif kind == "DONE" and len(fields) == 4 and self.status == "playing":
            score, miss = map(int, fields[2:])
            count = len(self.song["notes"])
            if not 0 <= miss <= count or not 50 * (count - miss) <= score <= 100 * (count - miss):
                raise ValueError("Invalid result")
            self.score, self.miss = score, miss
            self.elapsed = self.song["duration"]
            self.status = "finished"
        elif kind in ("STOP", "STARVED") and len(fields) == 2:
            self.status = "failed" if kind == "STARVED" else "quit"
            self.in_lobby = True

    def update(self, fields, now):
        # Telemetry is intentionally lossy. Invalid frames can be discarded.
        try:
            if len(fields) == 3 and fields[0] == "C" and self.inflight is not None:
                probe, anchor = map(int, fields[1:])
                if self.inflight != ("CLOCK", probe):
                    return
                rtt = now - self.probe_sent_at
                if 0 <= rtt <= MAX_CLOCK_RTT and 0 <= anchor <= 0xFFFFFFFF:
                    if self.sample is None or rtt < self.sample[0]:
                        self.sample = (rtt, self.probe_sent_at + rtt / 2, anchor)
            elif len(fields) == 6 and fields[0] == "T" and self.status == "playing":
                round_id, elapsed, score, combo, miss = map(int, fields[1:])
                count = len(self.song["notes"])
                if (
                    round_id == self.round
                    and self.elapsed <= elapsed <= self.song["duration"]
                    and self.score <= score <= count * 100
                    and 0 <= combo <= count
                    and self.miss <= miss <= count
                ):
                    self.elapsed, self.score, self.combo, self.miss = elapsed, score, combo, miss
        except ValueError:
            return

    def clock_pending(self):
        return (
            self.inflight is not None and self.inflight[0] == "CLOCK"
            or any(frame[0] == "CLOCK" for frame in self.pending)
        )

    def probe_clock(self):
        if not self.clock_pending() and self.probes < PROBES:
            self.probes += 1
            self.probe_sent_at = None
            self.queue("CLOCK", self.probes)

    def tick(self, now):
        frame = super().tick(now)
        if frame and self.inflight and self.inflight[0] == "CLOCK" and self.probe_sent_at is None:
            self.probe_sent_at = now
        return frame

    def schedule(self, target):
        _, midpoint, anchor = self.sample
        self.queue("AT", self.round, anchor, round((target - midpoint) * 1000))

    def cancel(self):
        if not self.connected:
            return
        # Keep reliable device-event acknowledgments, including a pending STOP.
        acknowledgments = [frame for frame in self.pending if frame[0] == "EA"]
        self.pending.clear()
        self.pending.extend(acknowledgments)
        self.queue("CANCEL", self.round)
        self.in_lobby = False
        self.status = "resetting"


class Match:
    """Two seats, one chart, one monotonic timebase and one audio player."""

    def __init__(self, songs, audio, offset_ms=0):
        self.songs, self.audio = songs, audio
        self.offset = offset_ms / 1000
        self.seats = [None, None]
        self.players = ()
        self.round_id = 0
        self.song = None
        self.phase = "lobby"
        self.notice = ""
        self.started_at = None
        self.ended_at = None
        self.audio_started = False

    def devices_ready(self):
        return all(player and player.connected and player.in_lobby for player in self.seats)

    def confirm(self, index):
        if self.phase != "lobby" or not self.devices_ready():
            raise ValueError("Both devices must be in the lobby")
        if type(index) is not int or not 0 <= index < len(self.songs):
            raise ValueError("Unknown song")
        song = self.songs[index]
        self.audio.load(song["wav"])
        self.round_id = (self.round_id + 1) % 65536
        self.players = tuple(self.seats)
        self.song = song
        self.phase = "readying"
        self.notice = ""
        self.started_at = None
        self.ended_at = None
        self.audio_started = False
        for player in self.players:
            player.begin(self.round_id, index)

    def reset_lobby(self):
        self.phase = "lobby"
        self.players = ()
        self.song = None
        self.started_at = None

    def abort(self, notice):
        self.audio.stop()
        for player in self.players:
            player.cancel()
        self.reset_lobby()
        self.notice = notice

    def tick(self, now):
        if self.phase == "lobby":
            return
        if self.phase == "results":
            if self.devices_ready():
                self.reset_lobby()
            return
        if self.phase != "playing" and any(player.status in TERMINAL for player in self.players):
            self.abort("start_interrupted")
            return
        if self.phase == "readying" and all(player.status == "ready" for player in self.players):
            self.phase = "clock"
            self.deadline = now + 4.0
        if self.phase == "clock":
            for player in self.players:
                player.probe_clock()
            if all(player.probes == PROBES and not player.clock_pending() for player in self.players):
                if not all(player.sample for player in self.players):
                    self.abort("sync_failed")
                    return
                self.started_at = now + COUNTDOWN
                self.phase = "schedule"
                for player in self.players:
                    player.schedule(self.started_at)
            elif now >= self.deadline:
                self.abort("sync_failed")
                return
        if self.phase in ("schedule", "commit") and now >= self.started_at - START_MARGIN:
            self.abort("sync_failed")
            return
        if self.phase == "schedule" and all(player.scheduled for player in self.players):
            for player in self.players:
                player.queue("GO", self.round_id)
            self.phase = "commit"
        if self.phase == "commit" and all(player.committed for player in self.players):
            self.phase = "countdown"
        if self.phase == "countdown" and now >= self.started_at:
            self.phase = "playing"
            for player in self.players:
                player.status = "playing"
        if self.phase in ("countdown", "playing") and not self.audio_started:
            if now >= self.started_at + self.offset:
                self.audio.play()
                self.audio_started = True
        if self.phase == "playing" and all(player.status in TERMINAL for player in self.players):
            self.audio.stop()
            self.ended_at = now
            self.phase = "results"

    def snapshot(self, now):
        phase = self.phase
        if phase == "lobby" and not self.devices_ready():
            phase = "waiting_devices"
        elif phase in ("clock", "schedule", "commit"):
            phase = "syncing"
        players = []
        for player in self.players or self.seats:
            status = player.status if player else "disconnected"
            if phase in ("lobby", "waiting_devices") and player and player.in_lobby:
                status = "idle"
            players.append({
                "status": status,
                "score": player.score if player and self.players else None,
                "combo": player.combo if player and self.players else None,
                "miss": player.miss if player and self.players else None,
            })
        duration = self.song["duration"] if self.song else 0
        latest = self.ended_at if self.phase == "results" else now
        elapsed = round((latest - self.started_at) * 1000) if self.started_at is not None else 0
        return {
            "phase": phase,
            "songs": [song["title"] for song in self.songs],
            "song": self.song["title"] if self.song else None,
            "players": players,
            "duration_ms": duration,
            "progress_ms": max(0, min(duration, elapsed)),
            "countdown": min(3, max(1, (-elapsed + 999) // 1000)) if phase == "countdown" else None,
            "notice": self.notice,
        }


def web_server(match, lock, port, stopping):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, status, content_type, body):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            files = {
                "/": ("index.html", "text/html"),
                "/style.css": ("style.css", "text/css"),
                "/console.js": ("console.js", "text/javascript"),
            }
            if self.path in files:
                name, content_type = files[self.path]
                self.respond(200, content_type + "; charset=utf-8", (WEB_DIR / name).read_bytes())
                return
            if self.path != "/events":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                previous = None
                last_sent = 0
                while not stopping.is_set():
                    now = time.monotonic()
                    with lock:
                        state = match.snapshot(now)
                    if state != previous or now - last_sent >= 5:
                        self.wfile.write(("data: " + json.dumps(state) + "\n\n").encode())
                        self.wfile.flush()
                        previous, last_sent = state, now
                    stopping.wait(0.2)
            except OSError:
                return

        def do_POST(self):
            if self.path != "/confirm":
                self.send_error(404)
                return
            if self.headers.get_content_type() != "application/json":
                self.send_error(415)
                return
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 0 < size <= 128:
                    raise ValueError("Invalid request body")
                self.connection.settimeout(2)
                index = json.loads(self.rfile.read(size))
                with lock:
                    match.confirm(index)
            except (TimeoutError, ValueError) as error:
                self.respond(409, "application/json", json.dumps(str(error)).encode())
                return
            except Exception as error:
                print("Unable to load audio:", error, flush=True)
                self.respond(500, "application/json", b'"Unable to load the song"')
                return
            self.respond(200, "application/json", b"null")

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def run(songs, audio, offset_ms, ports, web_port):
    import serial

    match = Match(songs, audio, offset_ms)
    lock, stopping = Lock(), Event()
    links = [None, None]
    paths = list(ports or (None, None))
    next_discovery = 0.0

    with web_server(match, lock, web_port, stopping) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(f"Multiplayer console: http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            while True:
                now = time.monotonic()
                if now >= next_discovery and None in links:
                    next_discovery = now + 1
                    if not ports:
                        seen = set(find_ports())
                        free = sorted(seen - set(paths))
                        for index, path in enumerate(paths):
                            if links[index] is None and path not in seen and free:
                                paths[index] = free.pop(0)
                    for index, path in enumerate(paths):
                        if path and links[index] is None:
                            try:
                                link = serial.Serial(path, 115200, timeout=0, write_timeout=0.05)
                            except OSError:
                                continue
                            links[index] = (link, now + 8)
                            with lock:
                                match.seats[index] = PlayerSession(songs)
                            print(f"Player {index + 1}: {path}", flush=True)
                with lock:
                    for index, connection in enumerate(links):
                        if connection is None:
                            continue
                        link, deadline = connection
                        player = match.seats[index]
                        try:
                            data = link.read(min(4096, link.in_waiting))
                            now = time.monotonic()
                            if data:
                                player.feed(data, now)
                            if player.session is None and now >= deadline:
                                raise ConnectionLost("No RH1 response")
                            frame = player.tick(now)
                            if frame is not None:
                                link.write(frame)
                        except (OSError, ConnectionLost) as error:
                            print(f"Player {index + 1}: {error}", flush=True)
                            player.disconnect()
                            link.close()
                            links[index] = None
                    match.tick(time.monotonic())
                time.sleep(0.002)
        finally:
            stopping.set()
            server.shutdown()
            thread.join()
            for connection in links:
                if connection is not None:
                    connection[0].close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", action="append", help="Repeat for two explicit micro:bit ports")
    parser.add_argument("--songs", type=Path, default=DEFAULT_SONGS)
    parser.add_argument("--offset-ms", type=int, default=0, help="Positive delays PC audio")
    parser.add_argument("--web-port", type=int, default=8765)
    args = parser.parse_args()
    if args.port and (len(args.port) != 2 or len(set(args.port)) != 2):
        parser.error("Provide two distinct --port values or let the host auto-detect")
    if not -1000 <= args.offset_ms <= 1000:
        parser.error("--offset-ms must be between -1000 and 1000")
    if not 0 <= args.web_port <= 65535:
        parser.error("--web-port must be between 0 and 65535")
    songs = load_library(args.songs)
    audio = PygameAudio()
    try:
        run(songs, audio, args.offset_ms, args.port, args.web_port)
    finally:
        audio.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMultiplayer host stopped")
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
