import { clockProbes, terminal } from "./rh1.mjs";

export class BrowserMatch {
  seats = [null, null];
  players = [];
  round = 0;
  phase = "lobby";
  song = null;
  startAt = null;
  notice = "";

  constructor(songs, audio) {
    this.songs = songs;
    this.audio = audio;
  }

  get devicesReady() {
    return this.seats.every((seat) => seat?.connected && seat.inLobby);
  }

  checkSelection(index) {
    if (this.phase !== "lobby" || !this.devicesReady) {
      throw new Error("Both micro:bits must be in the lobby.");
    }
    if (!Number.isInteger(index) || !this.songs[index]) throw new Error("Invalid song.");
    return this.songs[index];
  }

  begin(index) {
    this.song = this.checkSelection(index);
    this.players = this.seats.slice();
    this.round = (this.round + 1) % 65536;
    this.phase = "readying";
    this.notice = "";
    for (const player of this.players) player.begin(this.round, this.song);
  }

  resetLobby() {
    this.phase = "lobby";
    this.players = [];
    this.song = this.startAt = null;
  }

  abort(reason) {
    this.audio.stop();
    for (const player of this.players) player.cancel();
    this.resetLobby();
    this.notice = reason;
  }

  tick(now) {
    if (this.phase === "lobby") return;
    if (this.phase === "results") {
      if (this.devicesReady) this.resetLobby();
      return;
    }

    const ended = (player) => terminal.has(player.status);
    if (this.phase !== "playing" && this.players.some(ended)) {
      this.abort("start_interrupted");
      return;
    }

    if (this.phase === "readying" && this.players.every((player) => player.status === "ready")) {
      this.phase = "clock";
      this.clockDeadline = now + 4000;
    }
    if (this.phase === "clock") {
      for (const player of this.players) player.probe();
      if (this.players.every((player) => player.probes === clockProbes && !player.clockPending)) {
        if (!this.players.every((player) => player.sample)) {
          this.abort("sync_failed");
          return;
        }
        this.startAt = now + 3500;
        for (const player of this.players) player.schedule(this.startAt);
        this.phase = "schedule";
      } else if (now >= this.clockDeadline) {
        this.abort("sync_failed");
      }
    }
    if (["schedule", "commit"].includes(this.phase) && now >= this.startAt - 2250) {
      this.abort("sync_failed");
      return;
    }
    if (this.phase === "schedule" && this.players.every((player) => player.scheduled)) {
      for (const player of this.players) player.commit();
      this.phase = "commit";
    }
    if (this.phase === "commit" && this.players.every((player) => player.committed)) {
      try {
        this.audio.schedule(this.startAt);
        this.phase = "countdown";
      } catch {
        this.abort("audio_failed");
        return;
      }
    }
    if (this.phase === "countdown" && now >= this.startAt) {
      this.phase = "playing";
      for (const player of this.players) player.status = "playing";
    }
    if (this.phase === "playing" && this.players.every(ended)) {
      this.audio.stop();
      this.endedAt = now;
      this.phase = "results";
    }
  }

  snapshot(now) {
    const inRound = this.players.length > 0;
    let phase = this.phase;
    if (phase === "lobby" && !this.devicesReady) phase = "waiting_devices";
    if (["clock", "schedule", "commit"].includes(phase)) phase = "syncing";
    const song = this.song;
    const duration = song?.duration ?? 0;
    const at = phase === "results" ? this.endedAt : now;
    const elapsed = this.startAt === null ? 0 : Math.round(at - this.startAt);
    return {
      phase,
      songs: this.songs.map(({ title, duration, notes }) => ({
        title, duration_ms: duration, notes: notes.length,
      })),
      song: song?.title ?? null,
      note_count: song?.notes.length ?? 0,
      players: (inRound ? this.players : this.seats).map((player) => ({
        status: !inRound && player?.inLobby ? "idle" : player?.status ?? "disconnected",
        score: inRound ? player.score : null,
        combo: inRound ? player.combo : null,
        best_combo: inRound ? player.bestCombo : null,
        miss: inRound ? player.miss : null,
      })),
      duration_ms: duration,
      progress_ms: Math.min(duration, Math.max(0, elapsed)),
      countdown: phase === "countdown" ? Math.max(1, Math.min(3, Math.ceil(-elapsed / 1000))) : null,
      notice: this.notice,
    };
  }
}
