"""Time-based, row-major progress through both actual game backends."""

import struct
import unittest

from test_runtime import Harness, MatrixImage, Screen

NOTES = [(1000, 0), (3000, 1)]


class RecordingDisplay:
    def __init__(self, harness):
        self.harness = harness
        self.frames = []
        self.non_images = []

    def show(self, value):
        if isinstance(value, MatrixImage):
            self.frames.append((self.harness.clock, list(value.pixels)))
        else:
            self.non_images.append((self.harness.clock, value))


def run_round(pc=True, duration=5000, pause_at=None, perfect=False):
    h = Harness(notes=NOTES, duration=duration)
    b = h.board
    if pc:
        h.connect()
        h.select()
    else:
        b["CHART"] = b"".join(
            struct.pack("<HB", delta, direction)
            for delta, direction in ((1000, 0), (2000, 1))
        )
        b["SONG_LENGTH_MS"] = duration
    t0 = h.clock + 3500

    def raw_time():
        return b["ticks_diff"](h.clock, b["sync_at"]) if pc else h.clock - t0

    def song_time():
        raw = raw_time()
        return raw - (1000 if pause_at is not None and raw >= pause_at + 1000 else 0)

    def joy():
        if pc and not b["synced"]:
            return -1
        raw = raw_time()
        if pause_at is not None:
            if pause_at <= raw < pause_at + 50:
                return 3
            if pause_at + 1000 <= raw < pause_at + 1050:
                return 1
        return 3 if song_time() > duration + 1200 else -1

    h.joy = joy
    h.button = lambda lane: perfect and any(
        d == lane and t <= song_time() < t + 50 for t, d in NOTES
    )
    b["display"] = display = RecordingDisplay(h)
    b["play"](Screen(), Screen())
    # sync_at remains the original PC reference; active elapsed excludes pauses.
    return h, display, b["sync_at"] if pc else t0


class IndicatorTests(unittest.TestCase):
    def assert_fill(self, display):
        self.assertEqual(len(display.frames), 26)
        for count, (_, pixels) in enumerate(display.frames):
            self.assertEqual(pixels, [9] * count + [0] * (25 - count), count)

    def assert_times(self, display, t0, duration, pause_at=None):
        self.assert_fill(display)
        for count, (at, _) in enumerate(display.frames):
            expected = count * duration / 25
            if pause_at is not None and expected >= pause_at:
                expected += 1000
            self.assertGreaterEqual(at - t0, expected)
            self.assertLess(at - t0, expected + 20)
        self.assertTrue(all(at < display.frames[0][0] for at, _ in display.non_images))

    def test_pc_uses_each_song_duration_and_fills_rows_left_to_right(self):
        for duration in (5000, 10000):
            with self.subTest(duration=duration):
                _, display, t0 = run_round(duration=duration)
                self.assert_times(display, t0, duration)

    def test_standalone_starts_empty_and_reaches_25_at_the_song_end(self):
        _, display, t0 = run_round(pc=False, duration=7500)
        self.assert_times(display, t0, 7500)

    def test_pause_during_countdown_does_not_advance_progress(self):
        _, display, t0 = run_round(pause_at=-2000)
        self.assert_times(display, t0, 5000, pause_at=-2000)

    def test_pause_during_music_freezes_matrix_and_excludes_pause_time(self):
        _, display, t0 = run_round(pause_at=1200)
        self.assert_times(display, t0, 5000, pause_at=1200)
        self.assertFalse(any(1200 <= at - t0 < 2200 for at, _ in display.frames))

    def test_perfect_or_missed_notes_do_not_change_time_based_progress(self):
        _, missed, missed_t0 = run_round(perfect=False)
        _, perfect, perfect_t0 = run_round(perfect=True)
        self.assertEqual(
            [(at - missed_t0, pixels) for at, pixels in missed.frames],
            [(at - perfect_t0, pixels) for at, pixels in perfect.frames],
        )


if __name__ == "__main__":
    unittest.main()
