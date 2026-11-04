"""Exercise actual board transport/game code against the actual host controller."""

import ast
import copy
import importlib.util
import io
from pathlib import Path
import struct
import sys
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pc_host import HostSession, ConnectionLost

spec = importlib.util.spec_from_file_location("unified_build", ROOT / "tools/build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class Audio:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.calls.append((name, args))


class Screen:
    def __getattr__(self, name):
        return lambda *args: None


class Harness:
    def __init__(self, notes=None, duration=60000):
        self.clock = 0
        self.incoming = bytearray()
        self.outgoing = bytearray()
        self.max_rx = 0
        self.audio = Audio()
        self.music = Audio()
        self.results = []
        self.joy = lambda: -1
        self.button = lambda lane: False
        self.host_enabled = False
        self.connected = True
        self.host_error = None
        self.drop_ack = False
        self.drop_event = False
        self.drop_notes = False
        self.modes = []
        self.nonce = 0
        self.on_step = lambda: None
        outer = self

        class Pin:
            PULL_UP = 1

            def __init__(self, lane=None):
                self.lane = lane

            def read_digital(self):
                return int(not outer.button(self.lane))

            def write_digital(self, value):
                pass

            def set_pull(self, value):
                pass

            def read_analog(self):
                return 500

        class UART:
            def any(self):
                return len(outer.incoming)

            def read(self, size):
                data = bytes(outer.incoming[:size])
                del outer.incoming[:size]
                return data

            def write(self, value):
                outer.outgoing.extend(
                    value.encode() if isinstance(value, str) else value
                )

        def getrandbits(bits):
            assert 1 <= bits <= 30, "micro:bit getrandbits supports at most 30 bits"
            self.nonce += 1
            return self.nonce

        env = {
            "ticks_ms": lambda: self.clock % (1 << 30),
            "ticks_add": lambda a, b: (a + b) % (1 << 30),
            "ticks_diff": lambda a, b: ((a - b + (1 << 29)) % (1 << 30)) - (1 << 29),
            "getrandbits": getrandbits,
            "music": self.music,
            "gc": SimpleNamespace(collect=lambda: None),
            "uart": UART(),
            "sleep": self.sleep,
            "display": Screen(),
            "Image": SimpleNamespace(SQUARE=0, HAPPY=1),
        }
        for number in (0, 1, 5, 8, 9, 11, 12, 13, 14, 15, 16):
            env["pin" + str(number)] = Pin()
        tree = ast.parse(builder.assembled_source())
        cut = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.For))
        nodes = [
            n
            for n in tree.body[:cut]
            if not isinstance(n, (ast.Import, ast.ImportFrom))
        ]
        exec(
            compile(ast.Module(body=nodes, type_ignores=[]), "<board-source>", "exec"),
            env,
        )
        env.update(
            {
                "DPADS": [Pin(i) for i in range(4)],
                "center_x": 0,
                "center_y": 0,
                "joy_direction": lambda *a: self.joy(),
                "led_off": lambda: None,
                "draw_hud": lambda *a: None,
                "judgement_feedback": lambda j, now: (env["ticks_add"](now, 130), 0),
                "menu_draw": lambda screen, heading, options, *a: self.results.append(
                    (heading, options)
                ),
            }
        )
        self.board = env
        self.notes = notes or [(1000 + i * 700, i % 4) for i in range(80)]
        self.duration = duration
        self.host = HostSession(
            [
                {
                    "title": "TEST SONG",
                    "duration": duration,
                    "notes": self.notes,
                    "wav": Path("fake.wav"),
                }
            ],
            self.audio,
            nonce="12345678",
            log=lambda _: None,
        )

    def bridge(self):
        now = self.clock / 1000
        data = bytes(self.outgoing)
        self.outgoing.clear()
        if not self.host_enabled:
            return
        if self.connected:
            for line in data.splitlines(keepends=True):
                if self.drop_ack and b",A," in line:
                    self.drop_ack = False
                    continue
                if self.drop_event and b",E," in line:
                    self.drop_event = False
                    continue
                self.host.feed(line, now)
        try:
            frame = self.host.tick(now)
        except ConnectionLost as error:
            self.host_error = error
            self.host.close()
            self.host_enabled = False
            return
        if frame is not None and self.connected:
            if self.drop_notes and b",N," in frame:
                return
            self.incoming.extend(frame)
            self.max_rx = max(self.max_rx, len(self.incoming))
            if self.max_rx > 64:
                raise AssertionError("Hardware UART RX buffer overflow")

    def sleep(self, ms):
        self.clock += max(10, ms)
        self.on_step()
        self.bridge()
        self.modes.append(
            (self.board["supervisor"].mode, self.board["supervisor"].phase)
        )
        if self.clock > 1000000:
            raise AssertionError("Game did not terminate")

    def advance(self, ms):
        end = self.clock + ms
        while self.clock < end:
            self.board["service"]()
            self.sleep(10)

    def connect(self):
        self.host_enabled = True
        self.advance(1500)
        assert self.board["supervisor"].mode == "pc"
        assert self.host.session is not None
        assert self.host.state == "MENU"

    def select(self):
        b = self.board
        b.update(round_id=1, screen_state="LOADING", queue=[], synced=False)
        b["supervisor"].set_phase("loading", self.clock)
        b["send_event"]("SELECT", 1, 0)
        self.advance(1200)
        assert b["screen_state"] == "ARMED", (b["screen_state"], self.host_error)


class RuntimeTests(unittest.TestCase):
    def test_bundle_is_current_reversible_and_within_budget(self):
        tree = ast.parse(builder.assembled_source())
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if isinstance(body, list) and body and isinstance(body[0], ast.Expr):
                value = body[0].value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    body.pop(0)
        original = ast.dump(tree)
        compact, restored = builder.compact_tree(copy.deepcopy(tree))
        self.assertEqual(ast.dump(restored), original)
        if sys.version_info[:2] == (3, 13):
            self.assertEqual(
                (ROOT / "deploy/main.py").read_text(),
                builder.staged_deployment(compact),
            )
        self.assertLessEqual(len(builder.staged_deployment(compact).encode()), 20000)
        blocks = builder.deployment_payload(builder.staged_deployment(compact))
        self.assertLessEqual(max(len(block.encode()) for block in blocks), 4000)
        payload = ast.Module(
            body=[n for block in blocks for n in ast.parse(block).body], type_ignores=[]
        )
        self.assertEqual(ast.dump(payload), ast.dump(ast.parse(compact)))
        loader_tree = ast.parse(builder.staged_deployment(compact))
        self.assertLess(len(list(ast.walk(loader_tree))), 200)
        ast.parse(compact, feature_version=(3, 10))
        # There are no filesystem/module dependencies in the importable file.
        imports = {
            n.module
            for n in ast.walk(ast.parse(compact))
            if isinstance(n, ast.ImportFrom)
        }
        self.assertEqual(imports, {"microbit", "utime", "random"})

    def test_loader_fails_explicitly_if_payload_comments_are_missing(self):
        with patch("builtins.open", lambda path: io.StringIO("# empty payload\n")):
            with self.assertRaisesRegex(ValueError, "Missing payload"):
                exec(compile(builder.LOADER, "<loader>", "exec"), {})

    def test_packed_assets_match_original_standalone_exactly(self):
        h = Harness()
        original = ast.parse(
            (ROOT.parent / "standalone/src/microbit_main.py").read_text()
        )
        names = {"MELODY", "CHART", "SONG_LENGTH_MS", "FREQUENCIES"}
        nodes = [
            n
            for n in original.body
            if (isinstance(n, ast.FunctionDef) and n.name in ("unhexlify", "unpack"))
            or (
                isinstance(n, ast.Assign)
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id in names
            )
        ]
        namespace = {}
        exec(
            compile(
                ast.Module(body=nodes, type_ignores=[]), "<original-assets>", "exec"
            ),
            namespace,
        )
        self.assertIsNone(h.board["MELODY"])
        h.board["load_melody"]()
        self.assertIsInstance(h.board["MELODY"], bytearray)
        for key in ("MELODY", "CHART", "SONG_LENGTH_MS"):
            self.assertEqual(h.board[key], namespace[key])
        for pitch in set(h.board["MELODY"][4::5]):
            self.assertEqual(
                h.board["FREQUENCIES"][pitch], namespace["FREQUENCIES"][pitch]
            )

    def test_compact_font_matches_original_pixels_for_every_glyph(self):
        h = Harness()
        original = ast.parse(
            (ROOT.parent / "standalone/src/microbit_main.py").read_text()
        )
        font = next(
            ast.literal_eval(n.value)
            for n in ast.walk(original)
            if isinstance(n, ast.Assign)
            and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id == "font"
        )
        oled = h.board["OLED"].__new__(h.board["OLED"])
        for char in "".join(font) + "?":
            for scale in (1, 2):
                oled.buf = bytearray(1024)
                oled.text(char, 3, 7, scale)
                expected = bytearray(1024)
                for y, row in enumerate(font.get(char, font[" "])):
                    for x in range(3):
                        if row & (1 << (2 - x)):
                            for sy in range(scale):
                                for sx in range(scale):
                                    xx, yy = 3 + x * scale + sx, 7 + y * scale + sy
                                    expected[xx + (yy >> 3) * 128] |= 1 << (yy & 7)
                self.assertEqual(oled.buf, expected, (char, scale))

    def test_pc_mode_never_unpacks_local_melody_and_stop_releases_it(self):
        h = Harness()
        h.connect()
        h.select()
        self.assertIsNone(h.board["MELODY"])
        h.board["load_melody"] = lambda: self.fail("PC must not unpack local melody")
        h.board["outputs_off"]()
        self.assertIsNone(h.board["MELODY"])

    def test_actual_minified_file_boots_connects_and_plays_pc_round(self):
        self.run_deployment(pc=True)

    def test_actual_minified_file_plays_local_music_and_exits_pause(self):
        self.run_deployment(pc=False)

    def run_deployment(self, pc):
        # Execute the delivered file unchanged with fake native modules. This
        # catches renamed attribute/API mistakes that AST reversibility cannot.
        h = Harness(notes=[(1000, 0)], duration=2500)
        h.host_enabled = pc
        microbit = ModuleType("microbit")
        for name, value in h.board.items():
            if name.startswith("pin") or name in ("display", "Image", "uart"):
                setattr(microbit, name, value)
        microbit.i2c = SimpleNamespace(init=lambda **kw: None, write=lambda *a: None)
        microbit.uart.init = lambda **kw: None

        def joy():
            if pc:
                return 1 if 2000 <= h.clock < 2050 or 3500 <= h.clock < 3550 else -1
            for stamp, direction in (
                (2000, 1),
                (6000, 3),
                (7000, 1),
                (8000, 3),
                (9000, 2),
            ):
                if stamp <= h.clock < stamp + 50:
                    return direction
            return -1

        microbit.pin0.read_analog = lambda: 500 + (
            400 if joy() == 1 else -400 if joy() == 3 else 0
        )
        microbit.pin1.read_analog = lambda: 500 + (-400 if joy() == 2 else 0)

        class Finished(Exception):
            pass

        def sleep(ms):
            h.clock += max(10, ms)
            h.bridge()
            if h.clock > 12000:
                raise Finished()

        microbit.sleep = sleep
        timer = ModuleType("utime")
        for key in ("ticks_ms", "ticks_add", "ticks_diff"):
            setattr(timer, key, h.board[key])
        random = ModuleType("random")
        random.getrandbits = h.board["getrandbits"]
        firmware = (ROOT / "deploy/main.py").read_text()

        def open_firmware(path):
            self.assertEqual(path, "main.py")
            return io.StringIO(firmware)

        with (
            patch.dict(
                sys.modules,
                {
                    "microbit": microbit,
                    "music": h.music,
                    "utime": timer,
                    "random": random,
                },
            ),
            patch("builtins.open", open_firmware),
        ):
            with self.assertRaises(Finished):
                exec(
                    compile(
                        (ROOT / "deploy/main.py").read_text(), "<flash-file>", "exec"
                    ),
                    {},
                )
        self.assertIsNone(h.host_error)
        if pc:
            self.assertEqual(h.host.state, "MENU")
            self.assertEqual([name for name, _ in h.audio.calls].count("play"), 1)
        else:
            self.assertTrue(any(name == "pitch" for name, _ in h.music.calls))
            self.assertEqual(h.music.calls[-1][0], "stop")
            self.assertFalse(h.audio.calls)
        self.assertLessEqual(h.max_rx, 64)

    def test_live_heartbeat_without_chart_delivery_cancels_starved_round(self):
        h = Harness()
        h.connect()
        h.select()
        h.host.add_notes = lambda *args: None
        h.board["play"](Screen(), Screen())
        h.advance(300)
        self.assertEqual(h.board["screen_state"], "MENU")
        self.assertEqual(h.board["supervisor"].mode, "pc")
        self.assertFalse(any(heading == "RESULT" for heading, _ in h.results))
        self.assertIsNone(h.host_error)
        self.assertEqual(h.audio.calls[-1][0], "stop")

    def test_boot_usb_only_and_foreign_protocol_do_not_enable_pc(self):
        h = Harness()
        h.incoming.extend(b"CATDONE\nRH1,ATTACH,ffffffff,12345678\n")
        h.advance(4000)
        self.assertEqual(h.board["supervisor"].mode, "standalone")

    def test_real_handshake_catalog_loss_replay_and_reconnect(self):
        h = Harness()
        h.connect()
        old_nonce, old_session = h.board["nonce"], h.host.session
        h.board["supervisor"].set_phase("paused", h.clock)
        h.board["screen_state"] = "PLAY"
        h.connected = False
        h.advance(3000)
        self.assertEqual(h.board["supervisor"].mode, "standalone")
        self.assertEqual(h.board["screen_state"], "MENU")
        self.assertNotEqual(h.board["nonce"], old_nonce)
        self.assertIsNotNone(h.host_error)
        h.incoming.extend(("RH1,ATTACH," + old_nonce + ",12345678\n").encode())
        h.advance(20)
        self.assertIsNone(h.board["supervisor"].lease.session)
        h.host = HostSession(
            h.host.songs, h.audio, nonce="abcdef12", log=lambda _: None
        )
        h.connected = True
        h.host_enabled = True
        h.advance(1800)
        self.assertEqual(h.board["supervisor"].mode, "pc")
        self.assertNotEqual(h.host.session, old_session)

    def test_lost_command_ack_and_event_retry_do_not_duplicate_notes(self):
        h = Harness()
        h.connect()
        h.drop_event = True
        h.board.update(round_id=1, screen_state="LOADING", queue=[], synced=False)
        h.board["supervisor"].set_phase("loading", h.clock)
        h.board["send_event"]("SELECT", 1, 0)
        h.advance(700)
        h.drop_ack = True
        h.advance(2400)
        self.assertEqual(h.board["screen_state"], "ARMED")
        self.assertEqual(h.board["next_note"], 24)
        self.assertEqual(len(h.board["queue"]), 24)
        self.assertIsNone(h.host_error)
        self.assertLessEqual(h.max_rx, 64)

    def test_full_pc_round_streams_all_notes_and_scores(self):
        h = Harness()
        h.connect()
        h.select()
        b = h.board
        h.button = lambda lane: any(
            d == lane and t <= b["ticks_diff"](h.clock, b["sync_at"]) < t + 50
            for t, d in h.notes
        )
        h.joy = lambda: (
            3
            if b["synced"]
            and b["ticks_diff"](h.clock, b["sync_at"]) > h.duration + 1200
            else -1
        )
        b["play"](Screen(), Screen())
        h.advance(300)
        result = next(options for heading, options in h.results if heading == "RESULT")
        self.assertEqual(result[0], "SCORE 8000")
        self.assertEqual(result[3], "MISS 0")
        self.assertEqual(b["next_note"], 80)
        self.assertEqual(b["screen_state"], "MENU")
        self.assertEqual(b["supervisor"].mode, "pc")
        self.assertTrue(any(name == "play" for name, _ in h.audio.calls))
        self.assertEqual(h.audio.calls[-1][0], "stop")
        self.assertLessEqual(h.max_rx, 64)
        self.assertIsNone(h.host_error)

    def test_pc_wrong_direction_is_miss_and_local_profile_is_preserved(self):
        h = Harness(notes=[(1000, 0)], duration=2500)
        h.connect()
        h.select()
        b = h.board
        h.button = (
            lambda lane: lane == 1
            and 1000 <= b["ticks_diff"](h.clock, b["sync_at"]) < 1050
        )
        h.joy = lambda: (
            3 if b["synced"] and b["ticks_diff"](h.clock, b["sync_at"]) > 3500 else -1
        )
        b["play"](Screen(), Screen())
        result = next(options for heading, options in h.results if heading == "RESULT")
        self.assertEqual(result[0], "SCORE 0")
        self.assertEqual(result[3], "MISS 1")

    def test_pc_countdown_pause_resume_delays_audio_and_notes_together(self):
        h = Harness(notes=[(1000, 0)], duration=2500)
        h.connect()
        h.select()
        b = h.board
        start = h.clock
        pause_start, resume_at = start + 600, start + 1600

        def joy():
            if pause_start <= h.clock < pause_start + 50:
                return 3
            if resume_at <= h.clock < resume_at + 50:
                return 1
            if b["synced"] and b["ticks_diff"](h.clock, b["sync_at"]) > 5000:
                return 3
            return -1

        h.joy = joy
        h.button = (
            lambda lane: lane == 0
            and 2000 <= b["ticks_diff"](h.clock, b["sync_at"]) < 2050
        )
        played_at = []
        h.audio.play = lambda: played_at.append(h.clock)
        b["play"](Screen(), Screen())
        result = next(options for heading, options in h.results if heading == "RESULT")
        self.assertEqual(result[0], "SCORE 100")
        self.assertEqual(len(played_at), 1)
        self.assertLess(abs(played_at[0] - (b["sync_at"] + 1000)), 80)

    def test_host_loss_while_paused_aborts_without_a_result_or_delayed_audio(self):
        h = Harness()
        h.connect()
        h.select()
        start = h.clock
        h.joy = lambda: 3 if start + 400 <= h.clock < start + 500 else -1
        h.on_step = lambda: (
            setattr(h, "connected", False) if h.clock >= start + 800 else None
        )
        h.board["play"](Screen(), Screen())
        h.advance(1000)
        self.assertEqual(h.board["supervisor"].mode, "standalone")
        self.assertEqual(h.board["screen_state"], "MENU")
        self.assertFalse(any(heading == "RESULT" for heading, _ in h.results))
        self.assertFalse(any(name == "play" for name, _ in h.audio.calls))
        self.assertIsNotNone(h.host_error)

    def test_host_attach_during_local_round_waits_through_pause_and_results(self):
        self.run_local(pause_start=1000, pause_duration=1000, attach=True)

    def test_full_local_round_with_pause_during_music(self):
        self.run_local(pause_start=10000, pause_duration=2000)

    def test_full_local_round_without_host(self):
        self.run_local()

    def run_local(self, pause_start=None, pause_duration=0, attach=False):
        h = Harness()
        b = h.board
        chart, stamp = [], 0
        for delta, lane in struct.iter_unpack("<HB", b["CHART"]):
            stamp += delta
            target = 3500 + stamp
            if pause_start is not None and target >= pause_start:
                target += pause_duration
            chart.append((target, lane))
        h.button = lambda lane: any(
            d == lane and t <= h.clock < t + 50 for t, d in chart
        )

        def joy():
            if pause_start is not None:
                if pause_start <= h.clock < pause_start + 50:
                    return 3
                if (
                    pause_start + pause_duration
                    <= h.clock
                    < pause_start + pause_duration + 50
                ):
                    return 1
            if h.clock > b["SONG_LENGTH_MS"] + 4500 + pause_duration:
                return 3
            return -1

        h.joy = joy
        if attach:
            h.on_step = lambda: (
                setattr(h, "host_enabled", True) if h.clock > 500 else None
            )
        b["play"](Screen(), Screen())
        result = next(options for heading, options in h.results if heading == "RESULT")
        self.assertEqual(result[0], "SCORE 11400")
        self.assertEqual(result[3], "MISS 0")
        self.assertEqual(b["supervisor"].mode, "pc" if attach else "standalone")
        self.assertFalse(
            any(mode == "pc" and phase != "menu" for mode, phase in h.modes)
        )
        self.assertEqual(h.music.calls[-1][0], "stop")
        self.assertIsNone(b["MELODY"])


if __name__ == "__main__":
    unittest.main()
