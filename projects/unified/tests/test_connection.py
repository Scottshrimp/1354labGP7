"""Offline connection and framing checks; no serial ports or audio are opened."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connection import ModeSupervisor, PeerLease, PC, STANDALONE
from protocol import LineFramer, encode_line

SESSION_A = "0123456789abcdef"
SESSION_B = "fedcba9876543210"


class ModeTests(unittest.TestCase):
    def setUp(self):
        self.mode = ModeSupervisor()

    def ready_host(self, now_ms=0):
        self.assertTrue(self.mode.attach_host(SESSION_A, now_ms))
        return self.mode.mark_host_ready(SESSION_A, now_ms)

    def test_boot_and_usb_without_handshake_stay_standalone(self):
        self.assertEqual(self.mode.mode, STANDALONE)
        self.assertEqual(self.mode.phase, "menu")
        self.assertEqual(self.mode.poll(100000), ())
        self.assertEqual(self.mode.mark_host_ready(SESSION_A, 100000), ())

    def test_attach_without_catalog_and_audio_readiness_does_not_switch(self):
        self.mode.attach_host(SESSION_A, 0)
        self.assertTrue(self.mode.heartbeat(SESSION_A, 500))
        self.assertEqual(self.mode.poll(500), ())
        self.assertEqual(self.mode.mode, STANDALONE)

    def test_ready_host_switches_once_at_menu(self):
        self.assertEqual(self.ready_host(), ("enter_pc",))
        self.assertEqual(self.mode.mode, PC)
        self.assertEqual(self.mode.poll(100), ())

    def test_standalone_round_and_results_are_not_interrupted_by_host(self):
        self.mode.set_phase("playing", 0)
        self.assertEqual(self.ready_host(), ())
        self.assertTrue(self.mode.pending_pc)
        for now_ms, phase in enumerate(("paused", "playing", "results"), 1):
            self.assertEqual(self.mode.set_phase(phase, now_ms * 100), ())
            self.assertEqual(self.mode.mode, STANDALONE)
        self.assertEqual(self.mode.set_phase("menu", 500), ("enter_pc",))

    def test_pending_host_expiry_keeps_standalone_round_running(self):
        self.mode.set_phase("playing", 0)
        self.ready_host()
        self.assertEqual(self.mode.poll(2500), ())
        self.assertEqual(self.mode.phase, "playing")
        self.assertFalse(self.mode.pending_pc)
        self.assertEqual(self.mode.set_phase("menu", 2501), ())

    def test_pc_loss_returns_to_standalone_from_every_phase(self):
        for phase in ("menu", "loading", "ready", "playing", "paused", "results"):
            with self.subTest(phase=phase):
                self.setUp()
                self.ready_host()
                self.mode.set_phase(phase, 1)
                expected = ("enter_standalone",)
                if phase in ("loading", "ready", "playing", "paused"):
                    expected = ("abort_pc_round",) + expected
                self.assertEqual(self.mode.poll(2500), expected)
                self.assertEqual(
                    (self.mode.mode, self.mode.phase), (STANDALONE, "menu")
                )
                self.assertEqual(self.mode.poll(3000), ())

    def test_explicit_detach_stops_pc_round_without_waiting_for_timeout(self):
        self.ready_host()
        self.mode.set_phase("playing", 1)
        self.assertEqual(self.mode.disconnect(SESSION_B), ())
        self.assertEqual(
            self.mode.disconnect(SESSION_A), ("abort_pc_round", "enter_standalone")
        )

    def test_current_session_heartbeats_keep_pc_mode_alive(self):
        self.ready_host()
        for now_ms in range(500, 10000, 500):
            self.assertTrue(self.mode.heartbeat(SESSION_A, now_ms))
            self.assertEqual(self.mode.poll(now_ms), ())
        self.assertEqual(self.mode.mode, PC)

    def test_stale_or_foreign_packets_do_not_renew_or_revive_host(self):
        self.ready_host()
        self.assertFalse(self.mode.heartbeat(SESSION_B, 1000))
        self.assertEqual(self.mode.mark_host_ready(SESSION_B, 1000), ())
        self.assertFalse(self.mode.heartbeat(SESSION_A, 2500))
        self.mode.poll(2500)
        self.assertEqual(self.mode.mark_host_ready(SESSION_A, 2501), ())
        self.assertEqual(self.mode.mode, STANDALONE)

    def test_reconnect_uses_a_fresh_session(self):
        self.ready_host()
        self.mode.poll(2500)
        self.assertTrue(self.mode.attach_host(SESSION_B, 2501))
        self.assertFalse(self.mode.heartbeat(SESSION_A, 2502))
        self.assertEqual(self.mode.mark_host_ready(SESSION_B, 2502), ("enter_pc",))

    def test_new_host_cannot_take_over_a_live_pc_round(self):
        self.ready_host()
        self.mode.set_phase("playing", 1)
        self.assertFalse(self.mode.attach_host(SESSION_B, 1000))
        self.assertEqual(self.mode.lease.session, SESSION_A)

    def test_duplicate_handshake_does_not_extend_lease_or_reset_readiness(self):
        self.ready_host()
        self.assertTrue(self.mode.attach_host(SESSION_A, 2000))
        self.assertTrue(self.mode.host_ready)
        self.assertEqual(self.mode.poll(2500), ("enter_standalone",))

    def test_wrap_safe_clock_can_be_supplied_by_runtime_adapter(self):
        period = 65536
        ticks_diff = lambda now, old: (now - old + period // 2) % period - period // 2
        mode = ModeSupervisor(ticks_diff=ticks_diff)
        mode.attach_host(SESSION_A, 65000)
        mode.mark_host_ready(SESSION_A, 65000)
        self.assertTrue(mode.heartbeat(SESSION_A, 100))
        self.assertEqual(mode.poll(2599), ())
        self.assertEqual(mode.poll(2600), ("enter_standalone",))

    def test_invalid_configuration_and_phases_fail_explicitly(self):
        with self.assertRaises(ValueError):
            PeerLease(timeout_ms=0)
        with self.assertRaises(ValueError):
            self.mode.attach_host("invalid", 0)
        with self.assertRaises(ValueError):
            self.mode.set_phase("unknown", 0)


class FramingTests(unittest.TestCase):
    def test_fragmented_lines_and_crlf(self):
        framer = LineFramer()
        self.assertEqual(framer.feed(b"RH1,PI"), [])
        self.assertEqual(framer.feed(b"NG,123\r"), [])
        self.assertEqual(
            framer.feed(b"\nRH1,PONG,123\n"), ["RH1,PING,123", "RH1,PONG,123"]
        )

    def test_long_or_non_ascii_line_cannot_turn_its_suffix_into_a_command(self):
        for invalid in (b"x" * 100, b"bad\xff", b"bad\x03", b"bad\rtext"):
            with self.subTest(invalid=invalid):
                framer = LineFramer()
                self.assertEqual(framer.feed(invalid + b"RH1,READY\nOK\n"), ["OK"])
                self.assertLessEqual(len(framer.buffer), 60)

    def test_max_length_line_and_disconnected_partial_frame(self):
        framer = LineFramer()
        self.assertEqual(framer.feed(b"x" * 60 + b"\n"), ["x" * 60])
        framer.feed(b"RH1,OLD")
        framer.reset()
        self.assertEqual(framer.feed(b"RH1,NEW\n"), ["RH1,NEW"])
        self.assertEqual(framer.feed(None), [])

    def test_encoding_rejects_injection_and_oversize_frames(self):
        self.assertEqual(
            encode_line("RH1", "PING", SESSION_A),
            b"RH1,PING," + SESSION_A.encode() + b"\n",
        )
        for fields in (
            ("RH1", "x\nREADY"),
            ("RH1", "a,b"),
            ("RH1", ""),
            ("x" * 61,),
            ("\u4e2d",),
        ):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                encode_line(*fields)
        with self.assertRaises(ValueError):
            LineFramer(64)


if __name__ == "__main__":
    unittest.main()
