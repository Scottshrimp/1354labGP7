"""Drive two copies of the real board loop with separate clocks and UART delays."""

import ast
from collections import deque
from pathlib import Path
from queue import Queue
from threading import Thread
from types import SimpleNamespace
import unittest

from test_runtime import Audio, Harness, builder
from multiplayer import Match, PlayerSession


class Finished(Exception):
    pass


GAME = ast.parse(builder.assembled_source())
FIRST_LOOP = next(i for i, node in enumerate(GAME.body) if isinstance(node, ast.For))
BOARD_LOOP = compile(ast.Module(GAME.body[FIRST_LOOP:], []), "<board-loop>", "exec")


class Board(Harness):
    def __init__(self, offset):
        super().__init__()
        self.offset = offset
        self.yielded = Queue()
        self.resume = Queue()
        self.board["ticks_ms"] = lambda: (self.clock + offset) % (1 << 30)
        self.board["i2c"] = SimpleNamespace(init=lambda **kw: None, write=lambda *args: None)
        self.board["uart"].init = lambda **kw: None
        self.board["sleep"] = self.yield_to_host
        self.thread = Thread(target=self.run, daemon=True)
        self.thread.start()
        self.wake_at = self.next_wake()

    def run(self):
        try:
            exec(BOARD_LOOP, self.board)
        except Finished:
            return
        except BaseException as error:
            self.yielded.put(error)

    def yield_to_host(self, ms):
        self.yielded.put(self.clock + max(5, ms))
        self.clock = self.resume.get()
        if self.clock is None:
            raise Finished()

    def next_wake(self):
        result = self.yielded.get(timeout=3)
        if isinstance(result, BaseException):
            raise result
        return result

    def step(self, now):
        if now >= self.wake_at:
            self.resume.put(now)
            self.wake_at = self.next_wake()

    def close(self):
        self.resume.put(None)
        self.thread.join(timeout=3)


class SerialPath:
    def __init__(self, board, player, delay):
        self.board, self.player = board, player
        self.delay = delay
        self.to_host, self.to_board = deque(), deque()
        self.drop_telemetry = False
        self.drop_command = None

    def step(self, now):
        board, player = self.board, self.player
        while self.to_board and self.to_board[0][0] <= now:
            board.incoming.extend(self.to_board.popleft()[1])
        board.step(now)
        if not player.connected:
            board.outgoing.clear()
            self.to_host.clear()
            self.to_board.clear()
            return
        for line in bytes(board.outgoing).splitlines(keepends=True):
            if self.drop_telemetry and b",T," in line:
                self.drop_telemetry = False
            else:
                self.to_host.append((now + self.delay, line))
        board.outgoing.clear()
        while self.to_host and self.to_host[0][0] <= now:
            player.feed(self.to_host.popleft()[1], now / 1000)
        frame = player.tick(now / 1000)
        if frame:
            if self.drop_command and self.drop_command in frame:
                self.drop_command = None
            else:
                self.to_board.append((now + self.delay, frame))


class MultiplayerTests(unittest.TestCase):
    def game(self, delay=15):
        self.now = 0
        self.audio_played = []
        self.audio = Audio()
        self.audio.play = lambda: self.audio_played.append(self.now)
        notes = [(1000 + i * 250, i % 4) for i in range(56)]
        songs = [{"title": "TEST SONG", "duration": 15000, "notes": notes, "wav": Path("fake.wav")}]
        self.match = Match(songs, self.audio)
        self.boards = [Board((1 << 30) - 5000), Board(124251)]
        for board in self.boards:
            self.addCleanup(board.close)
        self.match.seats = [PlayerSession(songs, log=lambda _: None) for _ in self.boards]
        self.paths = [
            SerialPath(self.boards[0], self.match.seats[0], 5),
            SerialPath(self.boards[1], self.match.seats[1], delay),
        ]

    def until(self, predicate, timeout=20000):
        deadline = self.now + timeout
        while not predicate() and self.now < deadline:
            self.now += 5
            for path in self.paths:
                path.step(self.now)
            self.match.tick(self.now / 1000)
        self.assertTrue(predicate(), self.match.snapshot(self.now / 1000))

    def advance(self, duration):
        target = self.now + duration
        self.until(lambda: self.now >= target, duration)

    def ready(self, board):
        board.joy = lambda: 1
        self.advance(50)
        board.joy = lambda: -1

    def hit_chart(self, limit):
        for board in self.boards:
            def button(lane, b=board):
                elapsed = b.board["ticks_diff"](b.board["ticks_ms"](), b.board["sync_at"])
                index, within = divmod(elapsed - 1000, 250)
                return 0 <= index < limit and within < 35 and lane == index % 4

            board.button = button

    def test_two_ready_inputs_start_one_synchronized_round_and_settle(self):
        self.game()
        with self.assertRaisesRegex(ValueError, "Both devices"):
            self.match.confirm(0)
        self.until(self.match.devices_ready)
        self.match.confirm(0)
        self.assertEqual(self.match.snapshot(self.now / 1000)["phase"], "readying")
        self.until(lambda: all(player.status == "waiting" for player in self.match.players))

        self.ready(self.boards[0])
        self.advance(800)
        self.assertEqual([p.status for p in self.match.players], ["ready", "waiting"])
        self.assertEqual(self.audio_played, [])

        self.paths[0].drop_telemetry = True
        self.paths[1].drop_command = b",GO,"
        self.hit_chart(56)
        self.ready(self.boards[1])
        self.until(lambda: self.match.phase == "playing")
        starts = []
        for board in self.boards:
            starts.append(
                board.clock + board.board["ticks_diff"](board.board["sync_at"], board.board["ticks_ms"]())
            )
        self.assertEqual(len(self.audio_played), 1)
        self.assertLessEqual(max(starts + self.audio_played) - min(starts + self.audio_played), 15)
        self.until(lambda: all(player.score >= 100 for player in self.match.players))
        live = self.match.snapshot(self.now / 1000)
        self.assertEqual(live["phase"], "playing")
        self.assertGreater(live["progress_ms"], 1000)
        self.assertTrue(all(player["score"] >= 100 for player in live["players"]))
        stale = self.match.players[0]
        stale.update(["T", str(self.match.round_id - 1), "12000", "9999", "0", "0"], self.now / 1000)
        self.assertLess(stale.score, 9999)
        self.until(lambda: self.match.phase == "results")
        self.assertEqual([(p.score, p.miss) for p in self.match.players], [(5600, 0), (5600, 0)])
        self.assertEqual(sum(name == "stop" for name, _ in self.audio.calls), 1)

        for board in self.boards:
            board.joy = lambda: 3
        self.until(lambda: self.match.phase == "lobby")
        self.assertTrue(self.match.devices_ready())
        self.assertIsNone(self.match.snapshot(self.now / 1000)["players"][0]["score"])
        self.match.confirm(0)
        self.until(lambda: all(player.status == "waiting" for player in self.match.players))
        self.assertEqual(self.match.round_id, 2)

    def test_unusable_clock_measurements_cancel_before_play(self):
        self.game(delay=45)
        self.until(self.match.devices_ready)
        self.match.confirm(0)
        self.until(lambda: all(player.status == "waiting" for player in self.match.players))
        for board in self.boards:
            self.ready(board)
        self.until(lambda: self.match.phase == "lobby")
        self.until(self.match.devices_ready)
        self.assertEqual(self.match.notice, "sync_failed")
        self.assertEqual(self.audio_played, [])
        self.assertTrue(all(board.board["screen_state"] == "MENU" for board in self.boards))

    def test_disconnect_during_play_leaves_other_player_and_audio_running(self):
        self.game()
        self.until(self.match.devices_ready)
        self.match.confirm(0)
        self.until(lambda: all(player.status == "waiting" for player in self.match.players))
        self.hit_chart(56)
        for board in self.boards:
            self.ready(board)
        self.until(lambda: self.match.phase == "playing")
        self.match.players[0].disconnect()
        self.advance(1800)
        self.assertEqual(len(self.audio_played), 1)
        self.assertNotIn(("stop", ()), self.audio.calls)
        self.assertGreater(self.match.players[1].score, 0)
        self.until(lambda: self.match.phase == "results")
        self.assertEqual([p.status for p in self.match.players], ["disconnected", "finished"])
        self.assertEqual(self.match.players[1].score, 5600)
