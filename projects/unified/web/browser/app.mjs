import { BoardSession } from "./rh1.mjs";
import { BrowserMatch } from "./match.mjs";

const MICROBIT = { usbVendorId: 0x0d28 };
const now = () => performance.now();

class Sound {
  context = null;
  buffer = null;
  source = null;
  loaded = null;

  async prepare(song) {
    this.context ??= new AudioContext({ latencyHint: "interactive" });
    // Called directly from the song-confirmation click, before awaiting fetch.
    await this.context.resume();
    if (song === this.loaded) return;
    const response = await fetch(song.audio);
    if (!response.ok) throw new Error("Couldn’t load the song. Try confirming it again.");
    this.buffer = await this.context.decodeAudioData(await response.arrayBuffer());
    this.loaded = song;
  }

  schedule(startAt) {
    const context = this.context;
    if (context?.state !== "running" || !this.buffer) throw new Error("Audio is not ready.");
    this.stop();
    const stamp = context.getOutputTimestamp?.();
    const when = stamp?.performanceTime > 0
      ? stamp.contextTime + (startAt - stamp.performanceTime) / 1000
      : context.currentTime + (startAt - now()) / 1000 -
        (context.baseLatency || 0) - (context.outputLatency || 0);
    if (when <= context.currentTime) throw new Error("Audio deadline missed.");
    const source = context.createBufferSource();
    source.buffer = this.buffer;
    source.connect(context.destination);
    source.onended = () => {
      source.disconnect();
      if (this.source === source) this.source = null;
    };
    source.start(when);
    this.source = source;
  }

  stop() {
    this.source?.stop();
    this.source = null;
  }
}

function nonce() {
  return Array.from(crypto.getRandomValues(new Uint8Array(4)), (byte) =>
    byte.toString(16).padStart(2, "0")).join("");
}

class SerialLink {
  board = new BoardSession(nonce());
  closed = false;
  writing = false;

  constructor(port, onFault) {
    this.port = port;
    this.onFault = onFault;
  }

  async open() {
    await this.port.open({ baudRate: 115200 });
    this.opened = true;
    this.reader = this.port.readable.getReader();
    this.writer = this.port.writable.getWriter();
    this.deadline = now() + 8000;
    void this.read();
  }

  async read() {
    try {
      while (!this.closed) {
        const { value, done } = await this.reader.read();
        if (done) break;
        this.board.feed(value, now());
      }
      if (!this.closed) this.onFault("USB disconnected.");
    } catch (error) {
      if (!this.closed) this.onFault(error.message);
    }
  }

  tick(time) {
    if (this.closed || !this.writer) return;
    try {
      if (!this.board.session && time >= this.deadline) {
        throw new Error("No game handshake. Flash the downloaded main.py and close the editor’s serial console.");
      }
      if (this.writing) {
        if (time - this.writeStarted >= 2500) throw new Error("USB serial write timed out.");
        return;
      }
      const frame = this.board.nextFrame(time);
      if (!frame) return;
      this.writing = true;
      this.writeStarted = time;
      void this.writer.write(frame).catch((error) => {
        if (!this.closed) this.onFault(error.message);
      }).finally(() => { this.writing = false; });
    } catch (error) {
      this.onFault(error.message);
    }
  }

  async close() {
    if (this.closed) return;
    this.closed = true;
    this.board.disconnect();
    await Promise.allSettled([this.reader?.cancel(), this.writer?.abort()]);
    this.reader?.releaseLock();
    this.writer?.releaseLock();
    if (this.opened) await this.port.close();
  }
}

export async function startBrowserHost(onSnapshot) {
  const serial = window.isSecureContext ? navigator.serial : null;
  const buttons = [1, 2].map((player) => document.getElementById("connect-" + player));
  const message = document.getElementById("usb-message");
  const setup = document.getElementById("web-setup");
  const audio = new Sound();
  const response = await fetch(new URL("./starter-beat.json", import.meta.url));
  if (!response.ok) throw new Error("The starter chart couldn’t be loaded. Reload the page to try again.");
  const demoSong = await response.json();
  demoSong.audio = new URL("./starter-beat.wav", import.meta.url);
  const match = new BrowserMatch([demoSong], audio);
  const links = [null, null];
  const remembered = [null, null];
  const assigned = (port) => links.some((link) => link?.port === port);
  let picking = false;
  let nextDisplay = 0;

  function display(time) {
    const snapshot = match.snapshot(time);
    setup.hidden = !["waiting_devices", "lobby", "results"].includes(snapshot.phase);
    buttons.forEach((button, index) => {
      const link = links[index];
      const player = index + 1;
      button.disabled = !serial || picking || Boolean(link);
      button.textContent = !link ? "Connect player " + player
        : link.board.status === "connecting" ? "Connecting player " + player + "…"
        : "Player " + player + " connected";
    });
    onSnapshot(snapshot, Boolean(serial));
  }

  async function attach(port, index) {
    if (links[index] || assigned(port)) return;
    const link = new SerialLink(port, (reason) => {
      if (links[index] !== link || link.closed) return;
      message.textContent = "Player " + (index + 1) + ": " + reason;
      void link.close().catch(() => {}).finally(() => {
        if (links[index] === link) links[index] = null;
        display(now());
      });
    });
    links[index] = link;
    remembered[index] = port;
    match.seats[index] = link.board;
    display(now());
    try {
      await link.open();
      message.textContent = "";
    } catch {
      link.onFault("Can’t open the serial port. Close the Python Editor or other Rhythm Hit tabs and try again.");
    }
  }

  async function restoreAuthorized() {
    let ports;
    try {
      ports = (await serial.getPorts()).filter((port) => port.getInfo().usbVendorId === MICROBIT.usbVendorId);
    } catch {
      return;
    }
    // Leave ambiguous devices to the chooser. During a visit, keep a
    // reconnecting board in its original seat even when the other stays on.
    if (picking || ports.length > 2) return;
    const unassigned = ports.filter((port) => !assigned(port));
    // Try previously mapped seats before choosing a free seat for a new port.
    unassigned.sort((a, b) => Number(remembered.includes(b)) - Number(remembered.includes(a)));
    for (const port of unassigned) {
      const knownSeat = remembered.indexOf(port);
      const vacant = links.findIndex((link, seat) => !link && !ports.includes(remembered[seat]));
      const index = knownSeat === -1 ? vacant : knownSeat;
      if (index !== -1) void attach(port, index);
    }
  }

  if (serial) {
    buttons.forEach((button, index) => {
      button.addEventListener("click", async () => {
        picking = true;
        display(now());
        try {
          const port = await serial.requestPort({ filters: [MICROBIT] });
          if (assigned(port)) {
            message.textContent = "This micro:bit is already assigned. Select the other board.";
          } else {
            await attach(port, index);
          }
        } catch (error) {
          if (error.name !== "NotFoundError") message.textContent = "Serial permission couldn’t be granted.";
        } finally {
          picking = false;
          display(now());
        }
      });
    });

    serial.addEventListener("connect", () => { void restoreAuthorized(); });
    serial.addEventListener("disconnect", (event) => {
      const port = event.port ?? event.target;
      links.find((link) => link?.port === port)?.onFault("USB disconnected.");
    });
    void restoreAuthorized();
    setInterval(() => {
      const time = now();
      for (const link of links) link?.tick(time);
      match.tick(time);
      if (time >= nextDisplay) {
        nextDisplay = time + 100;
        display(time);
      }
    }, 5);
  }
  display(now());

  return {
    async confirm(index) {
      const song = match.checkSelection(index);
      await audio.prepare(song);
      match.begin(index);
      display(now());
    },
  };
}
