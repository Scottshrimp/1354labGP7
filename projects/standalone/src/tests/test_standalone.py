"""Desktop checks of packed assets and the actual board scheduling logic."""
import ast
import json
import struct
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'src'


def board_namespace():
    tree = ast.parse((GAME / 'microbit_main.py').read_text())
    names = {'SONG_LENGTH_MS', 'MELODY', 'CHART', 'FREQUENCIES', 'LEAD_MS',
             'PERFECT_MS', 'GOOD_MS', 'FRAME_MS', 'queue', 'screen_state'}
    functions = {'unhexlify', 'unpack', 'u16', 'Melody', 'ChartReader', 'play'}
    nodes = [node for node in tree.body
             if (isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in functions)
             or (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets))]
    calls = []
    def stop(pin, /):
        calls.append(('stop', (pin,), {}))
    namespace = {'pin12': object(), 'music': SimpleNamespace(
        pitch=lambda *args, **kw: calls.append(('pitch', args, kw)),
        stop=stop)}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<board>', 'exec'), namespace)
    return namespace, calls


class StandaloneTests(unittest.TestCase):
    def setUp(self):
        self.board, self.calls = board_namespace()

    def test_deployment_preserves_source_ast_and_fits_flash_budget(self):
        source = ast.parse((GAME / 'microbit_main.py').read_text())
        for node in ast.walk(source):
            body = getattr(node, 'body', None)
            if isinstance(body, list) and body and isinstance(body[0], ast.Expr):
                value = body[0].value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    body.pop(0)
        deployment = (GAME / 'deploy/main.py').read_text()
        self.assertEqual(ast.dump(source), ast.dump(ast.parse(deployment)))
        self.assertLessEqual(len(deployment.encode()), 18000)

    def test_compression_round_trip_for_zeros_repeats_and_literals(self):
        import sys
        sys.path.insert(0, str(ROOT / 'src' / 'tools'))
        from build_song import compress
        for data in (b'', bytes(range(256)), b'\x00' * 400,
                     b'microbit' * 80, self.board['MELODY'], self.board['CHART']):
            self.assertEqual(self.board['unpack'](compress(data).hex()), data)

    def test_chart_matches_editor_json_and_is_gentle(self):
        chart = json.loads((ROOT / 'music/megalovania/chart.json').read_text())
        rows, timestamp = [], 0
        for delta, direction in struct.iter_unpack('<HB', self.board['CHART']):
            timestamp += delta
            rows.append({'time_ms': timestamp, 'direction': ('UP', 'RIGHT', 'DOWN', 'LEFT')[direction]})
        self.assertEqual(rows, chart['notes'])
        gaps = [b['time_ms'] - a['time_ms'] for a, b in zip(rows, rows[1:])]
        self.assertGreaterEqual(min(gaps), 1000)
        self.assertGreater(max(gaps), 5000)
        self.assertEqual(len(rows), 114)
        self.assertLess(rows[-1]['time_ms'], self.board['SONG_LENGTH_MS'])

    def test_streamed_chart_is_complete_and_bounded(self):
        reader = self.board['ChartReader']()
        rows = []
        while reader.index < len(self.board['CHART']) or self.board['queue']:
            reader.fill()
            self.assertLessEqual(len(self.board['queue']), 12)
            rows.append(self.board['queue'].pop(0)[:2])
        self.assertEqual(len(rows), 114)
        self.assertEqual(rows, sorted(rows))

    def test_music_events_fit_duration_and_do_not_overlap(self):
        start, previous_end = 0, 0
        for delta, duration, pitch in struct.iter_unpack('<HHB', self.board['MELODY']):
            start += delta
            self.assertGreaterEqual(start, previous_end)
            self.assertGreater(duration, 0)
            self.assertTrue(0 < pitch < 128)
            previous_end = start + duration
        self.assertLess(previous_end, self.board['SONG_LENGTH_MS'])

    def test_countdown_is_silent_and_music_uses_p12_without_blocking(self):
        melody = self.board['Melody']()
        melody.update(-3500)
        self.assertFalse(self.calls)
        melody.update(0)
        self.assertEqual(self.calls[-1][0], 'pitch')
        self.assertIs(self.calls[-1][2]['pin'], self.board['pin12'])
        self.assertFalse(self.calls[-1][2]['wait'])

    def test_pause_can_resume_inside_a_note_without_advancing_time(self):
        melody = self.board['Melody']()
        melody.update(20)
        cursor = melody.index
        melody.stop()
        self.assertEqual(self.calls[-1][0], 'stop')
        melody.update(20)
        self.assertEqual(melody.index, cursor)
        self.assertEqual(self.calls[-1][0], 'pitch')

    def test_delayed_frame_catches_up_and_song_ends_silently(self):
        melody = self.board['Melody']()
        for elapsed in range(-3500, self.board['SONG_LENGTH_MS'] + 200, 17):
            melody.update(elapsed)
        self.assertEqual(melody.index, len(self.board['MELODY']))
        self.assertFalse(melody.sounding)
        self.assertEqual(self.calls[-1][0], 'stop')

    def test_full_game_scores_all_cues_and_returns_to_menu(self):
        self.run_game()

    def test_full_game_pause_during_countdown_keeps_chart_synced(self):
        self.run_game(pause_start=1000, pause_duration=1000)

    def test_full_game_pause_during_music_keeps_chart_synced(self):
        self.run_game(pause_start=10000, pause_duration=2000)

    def run_game(self, pause_start=None, pause_duration=0):
        board = self.board
        clock = [0]
        duration = board['SONG_LENGTH_MS']
        chart = json.loads((ROOT / 'music/megalovania/chart.json').read_text())['notes']
        dirs = ('UP', 'RIGHT', 'DOWN', 'LEFT')
        targets = [[3500 + n['time_ms'] for n in chart if n['direction'] == direction] for direction in dirs]
        if pause_start is not None:
            targets = [[t + pause_duration if t >= pause_start else t for t in lane] for lane in targets]
        def joystick(x, y):
            if pause_start is not None:
                if pause_start <= clock[0] < pause_start + 60:
                    return 3
                if pause_start + pause_duration <= clock[0] < pause_start + pause_duration + 60:
                    return 1
            return 3 if clock[0] > duration + 4500 + pause_duration else -1
        class Pin:
            def __init__(self, lane=None):
                self.lane = lane
            def read_digital(self):
                return 0 if any(t <= clock[0] < t + 60 for t in targets[self.lane]) else 1
            def write_digital(self, value):
                pass
        class Screen:
            def __getattr__(self, name):
                return lambda *args: None
        results = []
        board.update({'running_time': lambda: clock[0],
                      'sleep': lambda ms: clock.__setitem__(0, clock[0] + max(20, ms)),
                      'joy_direction': joystick,
                      'center_x': 0, 'center_y': 0, 'DPADS': [Pin(i) for i in range(4)],
                      'display': Screen(), 'Image': SimpleNamespace(SQUARE=0), 'pin8': Pin(),
                      'led_off': lambda: None, 'draw_hud': lambda *a: None,
                      'judgement_feedback': lambda j, now: (now + 130, 0),
                      'menu_draw': lambda screen, heading, options, *a: results.append((heading, options))})
        board['play'](Screen(), Screen())
        result = next(options for heading, options in results if heading == 'RESULT')
        self.assertEqual(result[0], 'SCORE 11400')
        self.assertEqual(result[3], 'MISS 0')
        self.assertEqual(board['screen_state'], 'MENU')
        self.assertFalse(self.calls[-1][0] == 'pitch')


if __name__ == '__main__':
    unittest.main()
