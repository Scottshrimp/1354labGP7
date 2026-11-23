const $ = (id) => document.getElementById(id);

const app = $("app");
const picker = $("picker");
const tracks = $("tracks");
const confirmButton = $("confirm");
const errorBox = $("error");
const countdown = $("countdown");
const count = $("count");
const lead = $("lead");
const browserSetup = $("web-setup");
let browserHost;

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const number = new Intl.NumberFormat("en-US");

const STEP = {
  boot: -1, waiting_devices: 0, lobby: 0, readying: 1,
  syncing: 2, countdown: 2, playing: 3, results: 4,
};

const STATUS = {
  disconnected: "Offline",
  connecting: "Connecting",
  idle: "In lobby",
  loading: "Loading chart",
  waiting: "Not ready",
  ready: "Ready",
  playing: "Playing",
  finished: "Finished",
  failed: "Chart lost",
  quit: "Quit",
  resetting: "Returning",
  dropped: "Dropped",
};

const IDLE = {
  disconnected: ["Connect over USB", "Pairs automatically when plugged in"],
  connecting: ["Handshaking", "Waiting for the device"],
  idle: ["In the lobby", "Waiting for a song"],
  loading: ["Loading chart", "Just a moment"],
  waiting: ["Push right on the device", "to ready up"],
  ready: ["Ready", "Waiting for opponent"],
  resetting: ["Returning to lobby", "Just a moment"],
  quit: ["Cancelled", "Back in the lobby soon"],
  failed: ["Chart transfer lost", "Back in the lobby soon"],
  dropped: ["Device dropped", "Plug it back in to reconnect"],
};

const NOTICE = {
  sync_failed: "The last round timed out while syncing and was cancelled. Pick a song again once both devices are back in the lobby.",
  start_interrupted: "The last round was cancelled before it started. Pick a song again once both devices are back in the lobby.",
  audio_failed: "Audio couldn’t start in time. Pick the song again to retry.",
};

const ERRORS = {
  "Both devices must be in the lobby": "Both devices need to be in the lobby to start.",
  "Unknown song": "That song is no longer available. Pick another one.",
};

const time = (ms) => {
  const seconds = Math.max(0, Math.floor(ms / 1000));
  return Math.floor(seconds / 60) + ":" + String(seconds % 60).padStart(2, "0");
};

let state = null;
let online = false;
let confirming = false;
let catalogKey = "";
let lastCount = null;

/* ---------- Player cards ---------- */

const cards = [1, 2].map((n) => {
  const root = $("player-" + n);
  const pick = (selector) => root.querySelector(selector);
  return {
    n,
    root,
    statusText: pick(".status-text"),
    idleView: pick(".idle-view"),
    idleText: pick(".idle-text"),
    scoreView: pick(".score-view"),
    score: pick(".score"),
    outcome: pick(".outcome"),
    combo: pick(".combo"),
    comboLabel: pick(".combo-label"),
    miss: pick(".miss"),
    acc: pick(".acc"),
    meter: pick(".meter-fill"),
    shown: 0,
    target: 0,
    frame: 0,
    lastCombo: 0,
    idleKey: "",
  };
});

function tweenScore(card, value) {
  if (value === card.target) return;
  card.target = value;
  cancelAnimationFrame(card.frame);
  if (reduceMotion.matches || value < card.shown) {
    card.shown = value;
    card.score.textContent = number.format(value);
    return;
  }
  const from = card.shown;
  const started = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - started) / 320);
    card.shown = Math.round(from + (value - from) * (1 - (1 - t) ** 3));
    card.score.textContent = number.format(card.shown);
    if (t < 1) card.frame = requestAnimationFrame(step);
  };
  card.frame = requestAnimationFrame(step);
}

function outcomes(players) {
  if (state.phase !== "results") return [null, null];
  const finished = players.map((p) => p.status === "finished");
  if (!finished[0] && !finished[1]) return ["dnf", "dnf"];
  if (finished[0] !== finished[1]) return finished.map((done) => (done ? "win" : "dnf"));
  const [a, b] = players.map((p) => p.score ?? 0);
  if (a === b) return ["tie", "tie"];
  return a > b ? ["win", "lose"] : ["lose", "win"];
}

const OUTCOME_LABEL = { win: "Winner", tie: "Tie", dnf: "DNF" };

function renderPlayers() {
  const players = state ? state.players : [{ status: "disconnected" }, { status: "disconnected" }];
  const phase = state ? state.phase : "boot";
  const inRound = ["countdown", "playing", "results"].includes(phase);
  const maxScore = (state?.note_count || 0) * 100;
  const result = state ? outcomes(players) : [null, null];

  players.forEach((player, index) => {
    const card = cards[index];
    let status = player.status;
    if (status === "disconnected" && player.score !== null && player.score !== undefined) status = "dropped";
    const showScore = inRound && player.score !== null && player.score !== undefined;

    card.root.dataset.status = status;
    card.root.dataset.outcome = result[index] || "";
    card.statusText.textContent = STATUS[status] || status;

    card.idleView.hidden = showScore;
    card.scoreView.hidden = !showScore;

    if (!showScore) {
      let [title, sub] = IDLE[status] || [STATUS[status] || "", ""];
      if (browserSetup && status === "disconnected") sub = "Choose this board above on your first visit";
      if (status === "idle" && phase === "waiting_devices") sub = "Waiting for the other device";
      if (status === "idle" && phase === "results") sub = "Waiting for opponent";
      const key = title + "|" + sub;
      if (key !== card.idleKey) {
        card.idleKey = key;
        const small = document.createElement("small");
        small.textContent = sub;
        card.idleText.replaceChildren(title, small);
      }
      card.lastCombo = 0;
      return;
    }

    tweenScore(card, player.score);
    const final = phase === "results";
    const combo = (final ? player.best_combo ?? player.combo : player.combo) ?? 0;
    card.comboLabel.textContent = final ? "Max combo" : "Combo";
    card.combo.textContent = number.format(combo);
    if (!final && combo > card.lastCombo && !reduceMotion.matches) {
      card.combo.classList.remove("bump");
      void card.combo.offsetWidth;
      card.combo.classList.add("bump");
    }
    card.lastCombo = combo;
    card.miss.textContent = number.format(player.miss ?? 0);
    const ratio = maxScore ? Math.min(1, player.score / maxScore) : 0;
    card.acc.textContent = (ratio * 100).toFixed(1) + "%";
    card.meter.style.width = (ratio * 100).toFixed(2) + "%";

    const kind = result[index];
    card.outcome.hidden = !OUTCOME_LABEL[kind];
    card.outcome.dataset.kind = kind || "";
    card.outcome.textContent = OUTCOME_LABEL[kind] || "";
  });

  renderLead(players, phase, result);
}

function renderLead(players, phase, result) {
  lead.replaceChildren();
  lead.dataset.leader = "";
  if (!["playing", "results"].includes(phase)) return;
  if (players.some((p) => p.score === null || p.score === undefined)) return;
  const [a, b] = players.map((p) => p.score);
  const strong = document.createElement("strong");
  if (phase === "results") {
    const winner = result.indexOf("win");
    if (winner === -1) {
      strong.textContent = result[0] === "tie" ? "Tie" : "No finish";
      lead.append(strong);
      return;
    }
    lead.dataset.leader = String(winner + 1);
    strong.textContent = "P" + (winner + 1) + " wins";
    const gap = Math.abs(a - b);
    lead.append(strong, !result.includes("dnf") && gap ? "+" + number.format(gap) : "");
    return;
  }
  if (players.some((p) => ["disconnected", "quit", "failed"].includes(p.status))) return;
  if (a === b) {
    strong.textContent = "Level";
    lead.append(strong);
    return;
  }
  const leader = a > b ? 1 : 2;
  lead.dataset.leader = String(leader);
  strong.textContent = "+" + number.format(Math.abs(a - b));
  lead.append(strong, "P" + leader + " leads");
}

/* ---------- Song picker ---------- */

function buildTracks(songs) {
  const key = JSON.stringify(songs);
  if (key === catalogKey) return;
  catalogKey = key;
  const previous = picker.elements.song?.value;
  tracks.replaceChildren(...songs.map((song, index) => {
    const info = typeof song === "string" ? { title: song } : song;
    const label = document.createElement("label");
    label.className = "track";
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "song";
    input.value = String(index);
    input.checked = previous === String(index);
    const body = document.createElement("span");
    body.className = "track-body";
    const no = document.createElement("span");
    no.className = "track-no";
    no.textContent = String(index + 1).padStart(2, "0");
    const title = document.createElement("span");
    title.className = "track-title";
    title.textContent = info.title;
    const meta = document.createElement("span");
    meta.className = "track-meta";
    if (info.duration_ms) {
      const length = document.createElement("span");
      length.textContent = time(info.duration_ms);
      const notes = document.createElement("span");
      notes.textContent = number.format(info.notes) + " notes";
      meta.append(length, notes);
    }
    body.append(no, title, meta);
    label.append(input, body);
    return label;
  }));
}

function selectedIndex() {
  const input = picker.querySelector("input[name=song]:checked");
  return input ? Number(input.value) : null;
}

function renderPicker() {
  const visible = state?.phase === "lobby";
  picker.hidden = !visible;
  if (!visible) return;
  buildTracks(state.songs);
  const locked = !online || confirming;
  for (const input of picker.querySelectorAll("input[name=song]")) input.disabled = locked;
  const index = selectedIndex();
  const selection = $("selection");
  if (index === null) {
    selection.textContent = "No song selected";
  } else {
    const song = state.songs[index];
    const strong = document.createElement("strong");
    strong.textContent = typeof song === "string" ? song : song.title;
    selection.replaceChildren("Selected: ", strong);
  }
  confirmButton.disabled = locked || index === null;
  confirmButton.setAttribute("aria-busy", String(confirming));
  confirmButton.firstElementChild.textContent = confirming ? "Loading…" : "Confirm song";
}

/* ---------- Stage ---------- */

function connectedCount() {
  return state.players.filter((p) => p.status !== "disconnected" && p.status !== "connecting").length;
}

function stageCopy() {
  if (!state) {
    if (browserSetup) return ["Setup", "Connect two micro:bits", "Plug in both boards and connect each player below."];
    return ["Connecting", "Connecting to host", "Start multiplayer.py in a terminal first."];
  }
  const song = state.song || "";
  switch (state.phase) {
    case "waiting_devices":
      return [
        "Waiting for devices · " + connectedCount() + " / 2",
        "Connect two micro:bits",
        "Plug both flashed devices into this computer over USB. Song selection opens once both reach the multiplayer menu.",
      ];
    case "lobby":
      return ["Lobby", "Pick a song", "Once confirmed, both devices load the chart and each player readies up on their own device."];
    case "readying":
      return ["Waiting for players", song, "Each player pushes right on their micro:bit to ready up. Pushing left on either cancels the round."];
    case "syncing":
      return ["Syncing", song, "Both players are ready. Aligning the two device clocks."];
    case "countdown":
      return ["Get ready", song, "Music plays from this computer."];
    case "playing":
      return ["Now playing", song, ""];
    case "results": {
      const result = outcomes(state.players);
      const winner = result.indexOf("win");
      const heading = winner >= 0 ? "Player " + (winner + 1) + " wins"
        : result[0] === "tie" ? "It’s a tie" : "Nobody finished";
      return ["Results · " + song, heading, "Push left on both devices to return to the lobby for the next round."];
    }
    default:
      return ["", "", ""];
  }
}

function renderStage() {
  const [eyebrow, heading, hint] = stageCopy();
  $("phase").textContent = eyebrow;
  $("heading").textContent = heading;
  $("hint").textContent = hint;
  $("hint").hidden = !hint;
  document.title = (heading && state ? heading + " · " : "") + "Rhythm Hit Versus";

  const notice = $("notice");
  const message = state && ["lobby", "waiting_devices"].includes(state.phase) ? NOTICE[state.notice] : "";
  notice.textContent = message || "";
  notice.hidden = !message;

  const step = STEP[state ? state.phase : "boot"];
  for (const item of $("steps").children) {
    const n = Number(item.dataset.step);
    item.className = n < step ? "done" : n === step ? "current" : "";
    if (n === step) item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
  }
}

function renderTimeline() {
  const visible = state && ["countdown", "playing", "results"].includes(state.phase);
  $("timeline").hidden = !visible;
  if (!visible) return;
  const duration = state.duration_ms || 1;
  const pct = Math.min(100, (state.progress_ms / duration) * 100);
  $("track-title").textContent = "Song progress";
  $("elapsed").textContent = time(state.progress_ms);
  $("duration").textContent = time(state.duration_ms);
  $("bar-fill").style.width = pct.toFixed(2) + "%";
  $("bar").setAttribute("aria-valuenow", String(Math.round(pct)));
}

function renderCountdown() {
  const value = state?.phase === "countdown" ? state.countdown : null;
  countdown.hidden = value === null || value === undefined;
  if (value === lastCount) return;
  lastCount = value;
  if (countdown.hidden) return;
  count.textContent = value;
  count.classList.remove("tick");
  void count.offsetWidth;
  count.classList.add("tick");
}

function render() {
  const link = $("connection");
  link.dataset.online = String(online);
  $("connection-text").textContent = browserSetup
    ? (online ? "Web Serial ready" : "Browser setup")
    : (online ? "Host connected" : state ? "Reconnecting…" : "Connecting…");
  app.dataset.phase = state ? state.phase : "boot";
  renderStage();
  renderPicker();
  renderTimeline();
  renderPlayers();
  renderCountdown();
}

/* ---------- Events ---------- */

picker.addEventListener("change", render);

picker.addEventListener("submit", async (event) => {
  event.preventDefault();
  const index = selectedIndex();
  if (index === null || confirming || state?.phase !== "lobby") return;
  confirming = true;
  errorBox.hidden = true;
  render();
  try {
    if (browserHost) {
      await browserHost.confirm(index);
      return;
    }
    const response = await fetch("/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(index),
    });
    if (!response.ok) {
      let detail = "";
      try { detail = await response.json(); } catch { /* non-JSON body */ }
      throw new Error(ERRORS[detail] || "Couldn’t confirm the song. Check both devices and the audio, then try again.");
    }
  } catch (error) {
    confirming = false;
    errorBox.textContent = error instanceof TypeError ? "Can’t reach the host." : error.message;
    errorBox.hidden = false;
    render();
  }
});

function displaySnapshot(latest, available) {
  if (latest.phase !== "lobby") {
    confirming = false;
    errorBox.hidden = true;
  }
  state = latest;
  online = available;
  render();
}

// The floating firmware card starts open on every load. Hiding it slides the
// card off the right edge and leaves a slim tab there to bring it back.
function setupFirmwareCard() {
  const card = $("firmware-card");
  const hide = $("firmware-hide");
  const show = $("firmware-show");
  if (!card || !hide || !show) return;
  const set = (collapsed, moveFocus = true) => {
    browserSetup.dataset.firmware = collapsed ? "collapsed" : "open";
    card.inert = collapsed;
    show.inert = !collapsed;
    if (moveFocus) (collapsed ? show : hide).focus({ preventScroll: true });
  };
  show.inert = true;
  hide.addEventListener("click", () => set(true));
  show.addEventListener("click", () => set(false));
  // Narrower layouts place the card inline, so it must never stay hidden there.
  matchMedia("(min-width: 1100px)").addEventListener("change", (event) => {
    if (!event.matches) set(false, false);
  });
}

if (browserSetup) {
  setupFirmwareCard();
  import("./browser/app.mjs")
    .then(({ startBrowserHost }) => startBrowserHost(displaySnapshot))
    .then((host) => { browserHost = host; })
    .catch((error) => { $("usb-message").textContent = error.message; });
} else {
  const events = new EventSource("/events");
  events.addEventListener("message", (event) => displaySnapshot(JSON.parse(event.data), true));
  events.addEventListener("error", () => {
    online = false;
    confirming = false;
    render();
  });
}

render();
