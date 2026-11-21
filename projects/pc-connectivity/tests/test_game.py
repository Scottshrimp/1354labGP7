import importlib.util
import json
import sys
import threading
import time
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pc_server', ROOT / 'src/server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
PERIOD = 1 << 30


def ticks():
    return int(time.monotonic() * 1000) % PERIOD


def diff(a, b):
    return (a - b + PERIOD // 2) % PERIOD - PERIOD // 2


class Pin:
    PULL_UP = 1
    def __init__(self): self.down = False; self.output = None
    def write_digital(self, value): self.output = value
    def read_digital(self): return 0 if self.down else 1
    def set_pull(self, value): pass


class UART:
    def __init__(self): self.out = bytearray()
    def write(self, line): self.out.extend(line.encode())
    def any(self): return False


class FakeBoard:
    def __init__(self):
        microbit = types.ModuleType('microbit')
        for name in ('pin13', 'pin11', 'pin15', 'pin5', 'pin8', 'pin9', 'pin14', 'pin16'):
            setattr(microbit, name, Pin())
        microbit.uart = UART()
        microbit.display = types.SimpleNamespace(value=None)
        microbit.display.show = lambda value: setattr(microbit.display, 'value', value)
        microbit.display.clear = lambda: setattr(microbit.display, 'value', None)
        utime = types.ModuleType('utime')
        utime.ticks_ms, utime.ticks_diff = ticks, diff
        utime.ticks_add = lambda a, b: (a + b) % PERIOD
        old_mb, old_ut = sys.modules.get('microbit'), sys.modules.get('utime')
        sys.modules['microbit'], sys.modules['utime'] = microbit, utime
        try:
            source = (ROOT / 'src/main.py').read_text().split('\nfor button in DPADS:')[0]
            self.env = {}
            exec(compile(source, 'device_main.py', 'exec'), self.env)
        finally:
            for name, old in (('microbit', old_mb), ('utime', old_ut)):
                if old is None: sys.modules.pop(name, None)
                else: sys.modules[name] = old
        self.env['render'] = lambda elapsed: None
        self.uart = microbit.uart
        self.mb = microbit
        self.pins = [microbit.pin13, microbit.pin11, microbit.pin15, microbit.pin5]
        self.closed = False

    def write(self, data):
        if self.closed: raise OSError('disconnected')
        self.env['command'](data.decode().strip(), ticks())

    def read(self, size):
        if self.closed: raise OSError('disconnected')
        self.env['service'](ticks())
        self.env['update'](ticks())
        result = bytes(self.uart.out[:size])
        del self.uart.out[:size]
        return result

    def close(self): self.closed = True


class Audio:
    def __init__(self): self.played = False; self.loaded = False
    def load(self, song): self.loaded = True
    def play(self): self.played = True
    def stop(self): self.played = False
    def close(self): pass


def wait_for(predicate, seconds=6):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result: return result
        time.sleep(.01)
    raise AssertionError('Timed out waiting for condition')


class GameTest(unittest.TestCase):
    def setUp(self):
        self.boards = {'P1': FakeBoard(), 'P2': FakeBoard()}
        self.ports = ['P1', 'P2']
        self.audio = Audio()
        self.song = server.load_library()[0]
        self.game = server.Game([self.song], self.audio,
            lambda port, *args, **kwargs: self.boards[port],
            lambda: [types.SimpleNamespace(device=p, vid=0x0D28, description='') for p in self.ports])
        wait_for(lambda: len(self.game.snapshot()['devices']) == 2)

    def tearDown(self):
        self.game.close()

    def prepare(self):
        self.game.request('prepare', '0')
        wait_for(lambda: self.game.snapshot()['phase'] == 'ready')

    def test_song_is_complete_on_both_boards_and_rejects_corruption(self):
        self.prepare()
        for board in self.boards.values():
            self.assertEqual(bytes(board.env['chart']), self.song['chart'])
            self.assertEqual(board.env['state'], 'READY')
        self.assertTrue(self.audio.loaded)
        bad = bytearray(self.song['chart'])
        bad[0], bad[1] = bad[1], bad[0]
        self.assertNotEqual(server.chart_checksum(bad), server.chart_checksum(self.song['chart']))

    def test_two_players_start_score_and_stop(self):
        self.prepare()
        self.game.request('start', 0)
        wait_for(lambda: self.game.snapshot()['phase'] == 'starting')
        board = self.boards['P1']
        self.assertEqual(self.boards['P2'].env['state'], 'START')
        wait_for(lambda: self.game.snapshot()['phase'] == 'playing', 7)
        # Jump the simulated board to its first note and press the required key.
        board.env['start_at'] = (ticks() - board.env['note_time'](0)) % PERIOD
        direction = board.env['chart'][3]
        board.pins[direction].down = True
        wait_for(lambda: board.env['score'] == 100)
        board.pins[direction].down = False
        wait_for(lambda: next(d for d in self.game.snapshot()['devices'] if d['port'] == 'P1')['score'] == 100)
        # The final STOP snapshot must capture updates newer than the last report.
        board.env['score'] = 150
        self.game.request('stop')
        wait_for(lambda: self.game.snapshot()['phase'] == 'finished')
        results = self.game.snapshot()['results']
        self.assertEqual(next(d for d in results if d['port'] == 'P1')['score'], 150)
        self.assertFalse(self.audio.played)

    def test_disconnect_aborts_and_keeps_result(self):
        self.prepare()
        self.ports.remove('P2')
        wait_for(lambda: self.game.snapshot()['phase'] == 'finished')
        snapshot = self.game.snapshot()
        self.assertEqual({r['port'] for r in snapshot['results']}, {'P1', 'P2'})
        self.assertIn('断开', snapshot['error'])
        self.assertFalse(self.audio.played)
        self.boards['P2'] = FakeBoard()
        self.ports.append('P2')
        wait_for(lambda: len(self.game.snapshot()['devices']) == 2, 4)
        self.assertIn('断开', self.game.snapshot()['error'])
        self.assertEqual({r['port'] for r in self.game.snapshot()['results']}, {'P1', 'P2'})

    def test_stop_during_transfer(self):
        self.game.request('prepare', '0')
        wait_for(lambda: self.game.snapshot()['phase'] == 'preparing')
        self.game.request('stop')
        wait_for(lambda: self.game.snapshot()['phase'] == 'finished')
        self.assertFalse(self.audio.played)


class ProtocolTest(unittest.TestCase):
    def test_retransmission_and_checksum_validation(self):
        board = FakeBoard()
        board.write(b'C,1,BEGIN,3,1,3000,0\n')
        board.write(b'C,2,DATA,0,01020304\n')
        board.write(b'C,2,DATA,0,01020304\n')
        self.assertEqual(bytes(board.env['chart']), b'\x01\x02\x03\x04')
        board.write(b'C,3,END\n')
        self.assertIn(b'A,3,ERR', board.uart.out)
        self.assertEqual(board.env['state'], 'LOAD')

    def test_full_chart_scoring_and_finish_with_wrapped_clock(self):
        board = FakeBoard()
        song = server.load_library()[0]
        device = server.Device('P1', lambda *args, **kwargs: board)
        device.prepare(song, 42)
        env = board.env
        env['start_at'] = PERIOD - 250
        env['state'] = 'PLAY'
        for index in range(song['count']):
            direction = env['chart'][index * 4 + 3]
            now = (env['start_at'] + env['note_time'](index)) % PERIOD
            board.pins[direction].down = True
            env['update'](now)
            board.pins[direction].down = False
            env['update']((now + 1) % PERIOD)
        env['update']((env['start_at'] + song['duration'] + 500) % PERIOD)
        self.assertEqual(env['state'], 'DONE')
        self.assertEqual(env['score'], song['count'] * 100)
        self.assertEqual(env['best'], song['count'])
        self.assertEqual(env['misses'], 0)

    def test_good_and_miss_reset_combo(self):
        board = FakeBoard()
        song = server.load_library()[0]
        device = server.Device('P1', lambda *args, **kwargs: board)
        device.prepare(song, 7)
        env = board.env
        env['start_at'] = ticks()
        env['state'] = 'PLAY'
        direction = env['chart'][3]
        board.pins[direction].down = True
        env['update']((env['start_at'] + env['note_time'](0) + 300) % PERIOD)
        self.assertEqual((env['score'], env['combo']), (50, 1))
        board.pins[direction].down = False
        env['update']((env['start_at'] + env['note_time'](1) + 401) % PERIOD)
        self.assertEqual((env['misses'], env['combo'], env['best']), (1, 0, 1))

    def test_feedback_countdown_judgements_and_cleanup(self):
        board = FakeBoard()
        song = server.load_library()[0]
        device = server.Device('P1', lambda *args, **kwargs: board)
        device.prepare(song, 8)
        env = board.env
        env['start_at'] = (PERIOD - 500) % PERIOD
        env['state'] = 'START'
        env['update']((env['start_at'] - 2500) % PERIOD)
        self.assertEqual(board.mb.display.value, '3')
        env['update'](env['start_at'])
        self.assertEqual(board.mb.display.value, '0')
        first = (env['start_at'] + env['note_time'](0)) % PERIOD
        board.pins[0].down = True
        env['update'](first)
        self.assertEqual((board.mb.pin9.output, board.mb.pin14.output, board.mb.pin8.output), (1, 0, 0))
        self.assertEqual(board.mb.display.value, '1')
        board.pins[0].down = False
        env['update']((first + 130) % PERIOD)
        self.assertEqual((board.mb.pin9.output, board.mb.pin14.output, board.mb.pin8.output), (1, 1, 0))
        second = (env['start_at'] + env['note_time'](1) + 300) % PERIOD
        board.pins[0].down = True
        env['update'](second)
        self.assertEqual((board.mb.pin9.output, board.mb.pin14.output, board.mb.pin8.output), (0, 0, 0))
        board.pins[0].down = False
        missed = (env['start_at'] + env['note_time'](2) + 401) % PERIOD
        env['update'](missed)
        self.assertEqual((board.mb.pin9.output, board.mb.pin14.output, board.mb.pin8.output), (0, 1, 1))
        self.assertEqual(board.mb.display.value, '0')
        board.write(b'C,12345,STOP\n')
        self.assertEqual((board.mb.pin9.output, board.mb.pin14.output, board.mb.pin8.output), (1, 1, 0))

    def test_disconnect_clears_feedback(self):
        board = FakeBoard()
        env = board.env
        env['judgement_feedback'](2, ticks())
        env['state'] = 'PLAY'
        env['last_host'] = (ticks() - 5000) % PERIOD
        env['service'](ticks())
        self.assertEqual(env['state'], 'FAULT')
        self.assertEqual((board.mb.pin9.output, board.mb.pin14.output, board.mb.pin8.output), (1, 1, 0))

    def test_host_timeout_is_fault(self):
        board = FakeBoard()
        board.env['state'] = 'READY'
        board.env['last_host'] = (ticks() - 5000) % PERIOD
        board.env['service'](ticks())
        self.assertEqual(board.env['state'], 'FAULT')


if __name__ == '__main__':
    unittest.main()
