"""AP/FC matrix behavior through the actual PC and standalone game loops."""

import struct
import unittest

from test_runtime import Harness, MatrixImage, Screen

FULL = [9] * 25
RING = MatrixImage.SQUARE.pixels
DARK = [0] * 25
NOTES = [(300, 0), (1300, 1), (2300, 2), (3300, 3), (4300, 0)]


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


def run_round(pc=True, actions=None, pause=False, harness=None):
    h = harness or Harness(notes=NOTES, duration=6000)
    b = h.board
    if pc:
        if harness is None:
            h.connect()
        h.select()
    else:
        data, previous = bytearray(), 0
        for stamp, direction in NOTES:
            data.extend(struct.pack("<HB", stamp - previous, direction))
            previous = stamp
        b["CHART"], b["SONG_LENGTH_MS"] = data, 6000
    start = h.clock + 3500

    def raw_time():
        return b["ticks_diff"](h.clock, b["sync_at"]) if pc else h.clock - start

    def song_time():
        raw = raw_time()
        return raw - (1000 if pause and raw >= 1600 else 0)

    def joy():
        if pc and not b["synced"]:
            return -1
        raw = raw_time()
        if pause and 600 <= raw < 650:
            return 3
        if pause and 1600 <= raw < 1650:
            return 1
        return 3 if song_time() > 7200 else -1

    h.joy = joy
    h.button = lambda lane: any(
        d == lane and t <= song_time() < t + 50 for t, d in actions or []
    )
    b["display"] = display = RecordingDisplay(h)
    b["play"](Screen(), Screen())
    h.advance(300)
    return h, display


class IndicatorTests(unittest.TestCase):
    def test_perfect_good_and_miss_change_full_to_ring_to_dark_in_both_modes(self):
        for pc in (False, True):
            with self.subTest(pc=pc):
                actions = [(300, 0), (1440 if pc else 1600, 1), (2300, 2), (4300, 0)]
                h, display = run_round(pc=pc, actions=actions)
                self.assertEqual(
                    [pixels for _, pixels in display.frames], [FULL, RING, DARK]
                )
                result = next(
                    options for heading, options in h.results if heading == "RESULT"
                )
                self.assertEqual(result[0], "SCORE 350")
                self.assertEqual(result[3], "MISS 1")

    def test_all_perfect_stays_full_without_combo_digits(self):
        h, display = run_round(actions=NOTES)
        self.assertTrue(all(at < h.board["sync_at"] for at, _ in display.non_images))
        self.assertEqual([pixels for _, pixels in display.frames], [FULL])

    def test_wrong_direction_breaks_fc_and_later_perfects_do_not_restore_it(self):
        h, display = run_round(actions=[(300, 1), *NOTES[1:]])
        self.assertEqual([pixels for _, pixels in display.frames], [FULL, DARK])
        self.assertEqual(h.board["screen_state"], "MENU")

    def test_pause_and_resume_preserve_indicator_instead_of_showing_pause_icon(self):
        _, display = run_round(actions=NOTES, pause=True)
        self.assertEqual([pixels for _, pixels in display.frames], [FULL])

    def test_new_round_resets_broken_fc_to_ap(self):
        h, display = run_round(actions=[])
        self.assertEqual([pixels for _, pixels in display.frames], [FULL, DARK])
        _, display = run_round(actions=NOTES, harness=h)
        self.assertEqual([pixels for _, pixels in display.frames], [FULL])


if __name__ == "__main__":
    unittest.main()
