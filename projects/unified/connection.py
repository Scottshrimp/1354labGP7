"""Hardware-independent controller for menu-only mode switching.

The board adapter supplies its wrap-safe ticks_diff function and must
poll this controller from every phase, including pauses and result screens.
Actions describe work for that adapter; this module does not control hardware.
"""

STANDALONE = "standalone"
PC = "pc"
PHASES = ("menu", "loading", "ready", "playing", "paused", "results")
HEARTBEAT_MS = 500
LEASE_TIMEOUT_MS = 2500


def _difference(now_ms, previous_ms):
    return now_ms - previous_ms


def _valid_session(session):
    return (
        isinstance(session, str)
        and len(session) == 16
        and all(char in "0123456789abcdef" for char in session)
    )


class PeerLease:
    """Only current-session heartbeats renew a live lease."""

    def __init__(self, timeout_ms=LEASE_TIMEOUT_MS, ticks_diff=None):
        if timeout_ms <= 0:
            raise ValueError("Lease timeout must be positive")
        self.timeout_ms = timeout_ms
        self.ticks_diff = ticks_diff or _difference
        self.clear()

    def clear(self):
        self.session = None
        self.last_seen_ms = None

    def alive(self, now_ms):
        if self.session is None:
            return False
        elapsed = self.ticks_diff(now_ms, self.last_seen_ms)
        return 0 <= elapsed < self.timeout_ms

    def attach(self, session, now_ms):
        if not _valid_session(session):
            raise ValueError("Session must contain 16 lowercase hexadecimal characters")
        if self.session is not None:
            # Retransmitted handshakes must not keep a dead host alive.
            return session == self.session and self.alive(now_ms)
        self.session = session
        self.last_seen_ms = now_ms
        return True

    def heartbeat(self, session, now_ms):
        if session != self.session or not self.alive(now_ms):
            return False
        self.last_seen_ms = now_ms
        return True


class ModeSupervisor:
    def __init__(self, timeout_ms=LEASE_TIMEOUT_MS, ticks_diff=None):
        self.lease = PeerLease(timeout_ms, ticks_diff)
        self.mode = STANDALONE
        self.phase = "menu"
        self.host_ready = False

    @property
    def pending_pc(self):
        return self.host_ready and self.mode == STANDALONE

    def attach_host(self, session, now_ms):
        """Called after a fresh challenge handshake; poll before dispatching input."""
        return self.lease.attach(session, now_ms)

    def heartbeat(self, session, now_ms):
        return self.lease.heartbeat(session, now_ms)

    def mark_host_ready(self, session, now_ms):
        """Adapter calls this after the catalog and host audio are ready."""
        if session != self.lease.session or not self.lease.alive(now_ms):
            return ()
        self.host_ready = True
        return self.poll(now_ms)

    def _lose_host(self):
        self.lease.clear()
        self.host_ready = False
        if self.mode != PC:
            return ()
        actions = ()
        if self.phase in ("loading", "ready", "playing", "paused"):
            actions = ("abort_pc_round",)
        self.mode = STANDALONE
        self.phase = "menu"
        return actions + ("enter_standalone",)

    def disconnect(self, session):
        if session is None or session != self.lease.session:
            return ()
        return self._lose_host()

    def poll(self, now_ms):
        if self.lease.session is not None and not self.lease.alive(now_ms):
            return self._lose_host()
        if self.host_ready and self.mode == STANDALONE and self.phase == "menu":
            self.mode = PC
            return ("enter_pc",)
        return ()

    def set_phase(self, phase, now_ms):
        if phase not in PHASES:
            raise ValueError("Unknown game phase")
        self.phase = phase
        return self.poll(now_ms)
