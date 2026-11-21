#!/usr/bin/env python3
"""Local two-player host for the independent PC connectivity firmware."""
import argparse
import importlib.util
import json
import hashlib
import queue
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
SONG = REPO / 'projects/standalone/music/megalovania'
LIBRARY = ROOT / 'songs.json'
MIDI_TOOL = REPO / 'projects/standalone/src/tools/build_song.py'
DIRECTIONS = {'UP': 0, 'RIGHT': 1, 'DOWN': 2, 'LEFT': 3}


def chart_checksum(data):
    a = b = 0
    for value in data:
        a = (a + value) % 255
        b = (b + a) % 255
    return (b << 8) | a


def load_song(directory=SONG):
    metadata = json.loads((directory / 'song.json').read_text(encoding='utf-8-sig'))
    doc = json.loads((directory / metadata['chart']).read_text(encoding='utf-8-sig'))
    duration = int(doc['duration_ms'])
    notes = sorted((int(n['time_ms']), DIRECTIONS[n['direction'].upper()]) for n in doc['notes'])
    if not 0 < len(notes) <= 2000 or not 0 < duration < 1 << 24:
        raise ValueError('Chart size or duration is unsupported')
    if any(t < 0 or t >= duration for t, _ in notes):
        raise ValueError('Note is outside the song')
    packed = bytearray()
    for stamp, direction in notes:
        packed.extend((stamp & 255, (stamp >> 8) & 255, stamp >> 16, direction))
    return {'title': metadata['title'], 'duration': duration, 'chart': bytes(packed),
            'count': len(notes), 'midi': directory / metadata['audio']}


def load_library():
    entries = json.loads(LIBRARY.read_text(encoding='utf-8'))
    if not isinstance(entries, list) or not entries:
        raise ValueError('Song library must contain at least one directory')
    songs = []
    for entry in entries:
        directory = (ROOT / entry).resolve()
        song = load_song(directory)
        song['id'] = str(len(songs))
        songs.append(song)
    return songs


def make_audio(song):
    cache = ROOT / '.cache'
    cache.mkdir(exist_ok=True)
    key = hashlib.sha256(str(song['midi'].resolve()).encode()).hexdigest()[:16]
    wav = cache / (key + '.wav')
    if not wav.exists() or wav.stat().st_mtime < song['midi'].stat().st_mtime:
        spec = importlib.util.spec_from_file_location('standalone_build', MIDI_TOOL)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        segments = module.melody_segments(song['midi'])[0]
        temp = cache / (key + '.preparing.wav')
        try:
            module.write_preview(temp, segments)
            temp.replace(wav)
        finally:
            temp.unlink(missing_ok=True)
    return wav


class DeviceError(RuntimeError):
    pass


class Device:
    def __init__(self, port, serial_factory):
        self.port = port
        self.link = serial_factory(port, 115200, timeout=0, write_timeout=0.5)
        self.lock = threading.Lock()
        self.seq = secrets.randbelow(10000)
        self.data = {'port': port, 'state': 'CONNECTING', 'score': 0, 'combo': 0,
                     'best': 0, 'misses': 0, 'progress': 0, 'error': ''}
        self.buffer = bytearray()
        self.offset = 0
        self.period = None

    def snapshot(self):
        return dict(self.data)

    def close(self):
        self.link.close()

    def _read(self):
        data = self.link.read(128)
        if not data:
            return []
        self.buffer.extend(data)
        if len(self.buffer) > 4096:
            raise DeviceError('Serial input too long')
        lines = []
        while b'\n' in self.buffer:
            raw, _, rest = self.buffer.partition(b'\n')
            self.buffer = bytearray(rest)
            try:
                parts = raw.decode('ascii').strip().split(',')
                if len(parts) == 7 and parts[0] == 'S':
                    rid, state, score, combo, best, misses = parts[1:]
                    self.data.update(round=int(rid), state=state, score=int(score),
                                     combo=int(combo), best=int(best), misses=int(misses))
                else:
                    lines.append(parts)
            except (UnicodeError, ValueError):
                continue
        return lines

    def command(self, action, *args):
        with self.lock:
            seq = self.seq
            self.seq = (self.seq + 1) % 65536
            line = ','.join(map(str, ('C', seq, action, *args))) + '\n'
            if len(line.encode()) > 61:
                raise DeviceError('Command exceeds serial frame limit')
            for _ in range(4):
                self.link.write(line.encode('ascii'))
                deadline = time.monotonic() + 0.8
                while time.monotonic() < deadline:
                    for parts in self._read():
                        if len(parts) == 3 and parts[:2] == ['A', str(seq)]:
                            if parts[2] == 'ERR':
                                raise DeviceError('Board rejected ' + action)
                            return parts[2]
                    time.sleep(0.002)
            raise DeviceError('No response to ' + action)

    def poll(self):
        with self.lock:
            self._read()

    def calibrate(self):
        self.period = int(self.command('CLOCK'))
        if self.period < 20000 or self.period & (self.period - 1):
            raise DeviceError('Unsupported board tick period')
        samples = []
        for _ in range(5):
            before = time.monotonic()
            tick = int(self.command('PING'))
            after = time.monotonic()
            midpoint_ms = (before + after) * 500
            samples.append((after - before, (tick - midpoint_ms) % self.period))
        self.offset = min(samples, key=lambda pair: pair[0])[1]

    def board_tick(self, host_time):
        return int(host_time * 1000 + self.offset) % self.period

    def prepare(self, song, round_id):
        chart = song['chart']
        self.data['progress'] = 0
        self.command('BEGIN', round_id, song['count'], song['duration'], chart_checksum(chart))
        for pos in range(0, len(chart), 16):
            self.command('DATA', pos, chart[pos:pos + 16].hex())
            self.data['progress'] = round(min(pos + 16, len(chart)) * 100 / len(chart))
        self.command('END')
        self.data.update(state='READY', progress=100)


class Game:
    """The worker owns serial links, audio, game state and queued UI commands."""
    ACTIVE = ('preparing', 'ready', 'starting', 'playing')

    def __init__(self, songs, audio, serial_factory, list_ports):
        self.songs, self.audio = songs, audio
        self.serial_factory, self.list_ports = serial_factory, list_ports
        self.devices = {}
        self.results = []
        self.phase = 'idle'
        self.error = ''
        self.round = 0
        self.audio_at = None
        self.expected_end = None
        self.selected = '0'
        self.tasks = queue.Queue()
        self.prepare_steps = None
        self.stop_event = threading.Event()
        self.worker = threading.Thread(target=self.loop, daemon=True)
        self.worker.start()

    def snapshot(self):
        # Copies are atomic enough for display; the worker alone mutates game state.
        devices = [d.snapshot() for d in list(self.devices.values())]
        return {'phase': self.phase, 'error': self.error, 'selected': self.selected,
                'songs': [{'id': s['id'], 'title': s['title']} for s in self.songs],
                'devices': devices, 'results': list(self.results)}

    def request(self, action, value=None):
        self.tasks.put((action, value))

    def abort(self, reason=''):
        self.audio.stop()
        self.audio_at = None
        self.prepare_steps = None
        self.phase = 'finished'
        self.error = reason
        for device in list(self.devices.values()):
            try:
                device.command('STOP')
                device.poll()
            except Exception as exc:
                device.data['error'] = str(exc)
        self.results = [d.snapshot() for d in self.devices.values()]

    def forget(self, port, reason):
        device = self.devices.pop(port, None)
        if device is None:
            return
        last = device.snapshot()
        last['state'] = 'DISCONNECTED'
        last['error'] = reason
        try:
            device.close()
        except Exception:
            pass
        if self.phase in self.ACTIVE:
            self.abort('设备断开，游戏已结束：' + port)
            self.results.append(last)
        else:
            self.error = '设备断开：' + port

    def scan(self):
        ports = [p.device for p in self.list_ports() if p.vid == 0x0D28 or
                 'micro:bit' in (p.description or '').lower() or
                 'microbit' in (p.description or '').lower()]
        for port in list(self.devices):
            if port not in ports:
                self.forget(port, 'USB disconnected')
        # Do not add late participants to an active round.
        if self.phase in self.ACTIVE:
            return
        for port in ports:
            if port in self.devices or len(self.devices) >= 2:
                continue
            device = None
            try:
                device = Device(port, self.serial_factory)
                device.calibrate()
                device.data['state'] = 'IDLE'
                self.devices[port] = device
                if self.phase == 'idle':
                    self.error = ''
            except Exception as exc:
                if device:
                    device.close()
                self.error = '无法连接 %s：%s' % (port, exc)

    def prepare(self, selected):
        if not self.devices or self.phase in ('preparing', 'starting', 'playing'):
            raise DeviceError('请先连接设备并结束当前游戏')
        song = next((song for song in self.songs if song['id'] == selected), None)
        if song is None:
            raise DeviceError('歌曲不存在')
        self.selected = selected
        self.phase = 'preparing'
        self.error = ''
        self.results = []
        self.round = (self.round + 1) % 65536
        self.audio.stop()
        self.prepare_steps = self.transfer(song)

    def transfer(self, song):
        chart = song['chart']
        for device in list(self.devices.values()):
            device.data['progress'] = 0
            device.command('BEGIN', self.round, song['count'], song['duration'], chart_checksum(chart))
            yield
            for pos in range(0, len(chart), 16):
                device.command('DATA', pos, chart[pos:pos + 16].hex())
                device.data['progress'] = round(min(pos + 16, len(chart)) * 100 / len(chart))
                yield
            device.command('END')
            device.data.update(state='READY', progress=100)
            yield
        self.audio.load(song)
        self.phase = 'ready'
        self.prepare_steps = None

    def start(self, offset_ms=0):
        if isinstance(offset_ms, bool) or not isinstance(offset_ms, int) or not -1000 <= offset_ms <= 1000:
            raise DeviceError('音频偏移必须为 -1000 至 1000 毫秒的整数')
        if self.phase != 'ready' or not self.devices or any(
                d.data['state'] != 'READY' for d in self.devices.values()):
            raise DeviceError('请先等待所有设备准备完成')
        for device in self.devices.values():
            device.calibrate()
        target = time.monotonic() + 5
        for device in self.devices.values():
            device.command('START', self.round, device.board_tick(target))
        if time.monotonic() >= target - 0.5:
            raise DeviceError('启动指令发送超时')
        self.audio_at = target + offset_ms / 1000
        song = next(s for s in self.songs if s['id'] == self.selected)
        self.expected_end = target + song['duration'] / 1000
        self.phase = 'starting'

    def loop(self):
        last_scan = last_ping = 0
        while not self.stop_event.wait(0.002):
            try:
                try:
                    action, value = self.tasks.get_nowait()
                except queue.Empty:
                    action = None
                if action == 'prepare':
                    self.prepare(value)
                elif action == 'start':
                    self.start(value)
                elif action == 'stop':
                    self.abort()
                now = time.monotonic()
                if now - last_scan >= 1:
                    self.scan()
                    last_scan = now
                for port, device in list(self.devices.items()):
                    try:
                        device.poll()
                    except Exception as exc:
                        self.forget(port, str(exc))
                if now - last_ping >= 0.5:
                    for port, device in list(self.devices.items()):
                        try:
                            device.command('PING')
                        except Exception as exc:
                            self.forget(port, str(exc))
                    last_ping = time.monotonic()
                if self.prepare_steps is not None:
                    try:
                        next(self.prepare_steps)
                    except StopIteration:
                        self.prepare_steps = None
                now = time.monotonic()
                if self.phase == 'starting' and now >= self.audio_at:
                    if now - self.audio_at > 0.15:
                        raise DeviceError('音频开始超时，请重新准备')
                    self.audio.play()
                    self.audio_at = None
                    self.phase = 'playing'
                if self.phase in ('starting', 'playing') and any(
                    d.data['state'] in ('IDLE', 'FAULT', 'LOAD') for d in self.devices.values()):
                    raise DeviceError('设备重启或通信超时')
                if self.phase == 'playing' and now < self.expected_end - 0.5 and any(
                    d.data['state'] == 'DONE' for d in self.devices.values()):
                    raise DeviceError('设备提前停止')
                if self.phase == 'playing' and self.devices and all(
                    d.data['state'] == 'DONE' for d in self.devices.values()):
                    self.audio.stop()
                    self.results = [d.snapshot() for d in self.devices.values()]
                    self.phase = 'finished'
            except Exception as exc:
                if self.phase in self.ACTIVE:
                    self.abort('游戏已停止：' + str(exc))
                else:
                    self.error = str(exc)

    def close(self):
        self.stop_event.set()
        self.worker.join(timeout=10)
        if self.worker.is_alive():
            raise RuntimeError('Device worker did not stop')
        self.audio.stop()
        for device in self.devices.values():
            device.close()
        self.audio.close()


class Audio:
    def __init__(self):
        import pygame
        pygame.mixer.init(44100, -16, 2, 512)
        self.mixer = pygame.mixer

    def load(self, song): self.mixer.music.load(str(song['wav']))
    def play(self): self.mixer.music.play()
    def stop(self): self.mixer.music.stop()
    def close(self): self.mixer.quit()


def handler_for(game, token):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, code, body, content_type):
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get('Host', '') == '127.0.0.1:%s' % self.server.server_port

        def do_GET(self):
            if not self.valid_host():
                self.respond(403, b'Forbidden', 'text/plain')
                return
            path = urlparse(self.path).path
            if path == '/api/state':
                body = game.snapshot()
                body['token'] = token
                self.respond(200, json.dumps(body).encode(), 'application/json')
            elif path == '/':
                self.respond(200, (ROOT / 'web/index.html').read_bytes(), 'text/html; charset=utf-8')
            else:
                self.respond(404, b'Not found', 'text/plain')

        def do_POST(self):
            origin = self.headers.get('Origin', '')
            host = self.headers.get('Host', '')
            if not self.valid_host() or self.headers.get('X-Game-Token') != token or origin != 'http://' + host:
                self.respond(403, b'Forbidden', 'text/plain')
                return
            path = urlparse(self.path).path
            try:
                if path == '/api/prepare':
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 256:
                        raise ValueError('Invalid request')
                    value = json.loads(self.rfile.read(length))['song']
                    game.request('prepare', value)
                elif path == '/api/start':
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 256:
                        raise ValueError('Invalid request')
                    value = json.loads(self.rfile.read(length))['offset_ms']
                    game.request('start', value)
                elif path == '/api/stop':
                    game.request('stop')
                else:
                    self.respond(404, b'Not found', 'text/plain')
                    return
                self.respond(200, b'{}', 'application/json')
            except Exception as exc:
                self.respond(400, json.dumps({'error': str(exc)}).encode(), 'application/json')

        def log_message(self, fmt, *args):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765, help='Local webpage port')
    args = parser.parse_args()
    import serial
    from serial.tools import list_ports
    songs = load_library()
    print('Preparing melody audio...', flush=True)
    for song in songs:
        song['wav'] = make_audio(song)
    audio = Audio()
    game = Game(songs, audio, serial.Serial, list_ports.comports)
    http = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(game, secrets.token_urlsafe(24)))
    print('Open http://127.0.0.1:%s' % args.port, flush=True)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()
        game.close()


if __name__ == '__main__':
    main()
