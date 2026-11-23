// RH1 is shared with protocol.py, pc_host.py and the micro:bit firmware.
const MAX_LINE = 60;
const MODULO = 65536;
const encoder = new TextEncoder();
const HEX8 = /^[0-9a-f]{8}$/;

export const terminal = new Set(["finished", "quit", "failed", "disconnected"]);
export const clockProbes = 4;

export function encode(...fields) {
  const line = fields.join(",");
  if (line.length > MAX_LINE || !fields.length ||
      fields.some((field) => !/^[\x20-\x2b\x2d-\x7e]+$/.test(String(field)))) {
    throw new Error("Invalid RH1 frame");
  }
  return encoder.encode(line + "\n");
}

export class LineFramer {
  line = "";
  discarded = false;
  cr = false;

  *feed(bytes) {
    for (const byte of bytes) {
      if (byte === 10) {
        const line = this.discarded ? "" : this.line;
        this.line = "";
        this.discarded = this.cr = false;
        if (line) yield line.split(",");
      } else if (!this.discarded) {
        if (byte === 13 && !this.cr) {
          this.cr = true;
        } else if (this.cr || byte < 32 || byte > 126 || this.line.length >= MAX_LINE) {
          this.discarded = true;
        } else {
          this.line += String.fromCharCode(byte);
        }
      }
    }
  }
}

function integer(value) {
  return /^\d+$/.test(value) ? Number(value) : NaN;
}

export class BoardSession {
  connected = true;
  inLobby = false;
  status = "connecting";
  score = 0;
  combo = 0;
  bestCombo = 0;
  miss = 0;
  elapsed = 0;
  pending = [];
  sequence = 0;
  eventSequence = 0;
  session = null;
  challenge = null;
  inflight = null;
  attachAt = -Infinity;
  sentAt = -Infinity;
  round = null;
  song = null;
  framer = new LineFramer();

  constructor(nonce) {
    if (!HEX8.test(nonce)) throw new Error("Invalid RH1 nonce");
    this.nonce = nonce;
  }

  disconnect() {
    this.connected = this.inLobby = false;
    if (!terminal.has(this.status)) this.status = "disconnected";
  }

  begin(round, song) {
    this.round = round;
    this.song = song;
    this.status = "loading";
    this.inLobby = false;
    this.score = this.combo = this.bestCombo = this.miss = this.elapsed = 0;
    this.cursor = 0;
    this.endQueued = false;
    this.probes = 0;
    this.sample = null;
    this.scheduled = this.committed = false;
    this.pending.push(["BEGIN", round, song.duration, song.notes.length]);
    this.queueNotes(40);
    this.pending.push(["ARM", round]);
  }

  queueNotes(count) {
    const end = Math.min(this.song.notes.length, this.cursor + count);
    while (this.cursor < end) {
      const index = this.cursor++;
      this.pending.push(["N", this.round, index, ...this.song.notes[index]]);
    }
    if (!this.endQueued && this.cursor === this.song.notes.length) {
      this.pending.push(["END", this.round]);
      this.endQueued = true;
    }
  }

  cancel() {
    if (!this.connected) return;
    this.pending = this.pending.filter(([kind]) => kind === "EA");
    this.pending.push(["CANCEL", this.round]);
    this.status = "resetting";
    this.inLobby = false;
  }

  get clockPending() {
    return this.inflight?.[0] === "CLOCK" ||
      this.pending.some(([kind]) => kind === "CLOCK");
  }

  probe() {
    if (!this.clockPending && this.probes < clockProbes) {
      this.probeSentAt = null;
      this.pending.push(["CLOCK", ++this.probes]);
    }
  }

  schedule(time) {
    this.pending.push(["AT", this.round, this.sample.anchor, Math.round(time - this.sample.midpoint)]);
  }

  commit() {
    this.pending.push(["GO", this.round]);
  }

  nextFrame(now) {
    if (!this.session) {
      if (!this.challenge || now - this.attachAt < 800) return null;
      this.attachAt = now;
      return encode("RH1", "ATTACH", this.challenge, this.nonce);
    }
    if (now - this.lastRx >= 2500) throw new Error("Device stopped responding.");
    if (this.inflight) {
      if (now - this.sentAt < 800) return null;
    } else {
      if (!this.pending.length && now - this.sentAt < 500) return null;
      this.inflight = this.pending.shift() ?? ["HB"];
    }
    if (this.inflight[0] === "CLOCK" && this.probeSentAt === null) {
      this.probeSentAt = now;
    }
    this.sentAt = now;
    return encode("RH1", this.session, this.sequence, ...this.inflight);
  }

  feed(bytes, now) {
    for (const [prefix, session, kind, ...fields] of this.framer.feed(bytes)) {
      if (prefix !== "RH1") continue;
      if (session === "HELLO" && !fields.length && HEX8.test(kind)) {
        if (this.session) throw new Error("Device restarted.");
        if (this.challenge !== kind) this.attachAt = -Infinity;
        this.challenge = kind;
      } else if (session === "ACCEPT" && !fields.length &&
                 this.challenge && kind === this.challenge + this.nonce) {
        if (!this.session) {
          this.session = kind;
          this.lastRx = now;
          this.pending.push(["DUO"]);
        }
      } else if (this.session && session === this.session) {
        this.receive(kind, fields, now);
      }
    }
  }

  receive(kind, fields, now) {
    if (kind === "A" && fields.length === 2 && this.inflight &&
        integer(fields[0]) === this.sequence) {
      if (fields[1] !== "OK") throw new Error("Device rejected " + this.inflight[0] + ". Check the game firmware.");
      switch (this.inflight[0]) {
        case "ARM":
          if (this.status === "loading") this.status = "waiting";
          break;
        case "AT": this.scheduled = true; break;
        case "GO": this.committed = true; break;
        case "CANCEL":
          this.song = this.round = null;
          this.status = "idle";
          this.inLobby = true;
          break;
      }
      this.inflight = null;
      this.sequence = (this.sequence + 1) % MODULO;
      this.lastRx = now;
    } else if (kind === "E" && fields.length >= 3) {
      const seq = integer(fields[0]);
      if (seq === this.eventSequence) {
        this.event(fields[1], fields.slice(2));
        this.eventSequence = (seq + 1) % MODULO;
      } else if (seq !== (this.eventSequence + MODULO - 1) % MODULO) {
        return;
      }
      if (!this.pending.some(([command, ack]) => command === "EA" && ack === seq)) {
        this.pending.unshift(["EA", seq]);
      }
      this.lastRx = now;
    } else if (kind === "C" && fields.length === 2 &&
               this.inflight?.[0] === "CLOCK" && integer(fields[0]) === this.inflight[1]) {
      const rtt = now - this.probeSentAt;
      const anchor = integer(fields[1]);
      if (rtt >= 0 && rtt <= 65 && anchor <= 0xffffffff &&
          (!this.sample || rtt < this.sample.rtt)) {
        this.sample = { rtt, anchor, midpoint: this.probeSentAt + rtt / 2 };
      }
    } else if (kind === "T" && fields.length === 5 && this.status === "playing") {
      const [round, elapsed, score, combo, miss] = fields.map(integer);
      const count = this.song.notes.length;
      if (round === this.round && elapsed >= this.elapsed && elapsed <= this.song.duration &&
          score >= this.score && score <= count * 100 && combo <= count &&
          miss >= this.miss && miss <= count) {
        Object.assign(this, { elapsed, score, combo, miss });
        this.bestCombo = Math.max(this.bestCombo, combo);
      }
    }
  }

  event(kind, [round, ...fields]) {
    if (this.round !== null && integer(round) !== this.round) return;
    if (kind === "LOBBY" && !fields.length) {
      this.inLobby = true;
      if (!this.song) this.status = "idle";
      return;
    }
    if (!this.song || terminal.has(this.status)) return;
    if (kind === "START" && !fields.length && this.status === "waiting") {
      this.status = "ready";
    } else if (kind === "NEED" && fields.length === 2 && this.status === "playing") {
      const [start, capacity] = fields.map(integer);
      if (!(start <= this.cursor && capacity <= 44)) throw new Error("Invalid chart refill.");
      if (!this.endQueued && this.inflight?.[0] !== "N" &&
          !this.pending.some(([command]) => command === "N")) {
        this.queueNotes(Math.min(12, capacity));
      }
    } else if (kind === "DONE" && (fields.length === 2 || fields.length === 3) && this.status === "playing") {
      const [score, miss, best = this.bestCombo] = fields.map(integer);
      const count = this.song.notes.length;
      const hits = count - miss;
      if (!(hits >= 0 && score >= 50 * hits && score <= 100 * hits &&
            (fields.length === 2 || best <= hits))) throw new Error("Invalid final score.");
      Object.assign(this, { score, miss, bestCombo: best, elapsed: this.song.duration, status: "finished" });
    } else if ((kind === "STOP" || kind === "STARVED") && !fields.length) {
      this.status = kind === "STARVED" ? "failed" : "quit";
      this.inLobby = true;
    }
  }
}
