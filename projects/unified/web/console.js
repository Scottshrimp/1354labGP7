import { accountsEnabled, currentUser, finishRun, loadAccount, mountAccountNav, onUserChange, openAuth, startRun } from "./account.mjs";

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
// Web Serial exists only in desktop Chromium browsers (Chrome, Edge, …) on HTTPS.
const serialUnsupported = Boolean(browserSetup) && !(window.isSecureContext && "serial" in navigator);
let browserHost;
let returning = false;
// Solo runs of a logged-in player are recorded for the leaderboard.
let accountReady = false;
let run = null;        // { id: Promise<run id | null> } for the current solo round
let runSave = null;    // { kind, text } shown on the results screen
const MODE_KEY = "rhythmhit.mode";
const MODE_NAME = { versus: "Versus", solo: "Solo" };
// Snapshots carry the live mode; before the first one, use the saved choice.
let mode = "versus";
try {
  if (browserSetup && localStorage.getItem(MODE_KEY) === "solo") mode = "solo";
} catch { /* storage unavailable */ }
const preferredMode = mode;
const isSolo = () => mode === "solo";

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

const SOLO_NOTICE = {
  sync_failed: "The last round timed out while syncing and was cancelled. Pick a song again once your micro:bit is back in the lobby.",
  start_interrupted: "The last round was cancelled before it started. Pick a song again once your micro:bit is back in the lobby.",
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
  if (isSolo()) {
    const [player] = players;
    if (player.status !== "finished") return ["dnf"];
    return [player.miss === 0 ? "fc" : null];
  }
  const finished = players.map((p) => p.status === "finished");
  if (!finished[0] && !finished[1]) return ["dnf", "dnf"];
  if (finished[0] !== finished[1]) return finished.map((done) => (done ? "win" : "dnf"));
  const [a, b] = players.map((p) => p.score ?? 0);
  if (a === b) return ["tie", "tie"];
  return a > b ? ["win", "lose"] : ["lose", "win"];
}

const OUTCOME_LABEL = { win: "Winner", tie: "Tie", dnf: "DNF", fc: "Full combo" };

function renderPlayers() {
  const players = state ? state.players
    : Array.from({ length: isSolo() ? 1 : 2 }, () => ({ status: "disconnected" }));
  cards[0].root.querySelector("h2").textContent = isSolo() ? "Solo player" : "Player 1";
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
      if (browserSetup && status === "disconnected") {
        sub = serialUnsupported ? "Needs desktop Chrome or Edge" : "Choose this board above on your first visit";
      }
      if (isSolo()) {
        if (status === "ready") sub = "Starting soon";
      } else {
        if (status === "idle" && phase === "waiting_devices") sub = "Waiting for the other device";
        if (status === "idle" && phase === "results") sub = "Waiting for opponent";
      }
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
  if (isSolo() || !["playing", "results"].includes(phase)) return;
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
  if (serialUnsupported) {
    return [
      "Browser not supported",
      "Open this page in Chrome or Edge",
      "This browser can’t talk to a micro:bit over USB. Safari, Firefox and phone browsers don’t support Web Serial, so open rhythmhit.scottshrimp.com in desktop Chrome or Edge to connect your boards. You can still download the firmware and read the tutorial here.",
    ];
  }
  if (isSolo()) return soloCopy();
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
      return ["Results · " + song, heading, "Head back to the lobby for the next round, or push left on both devices."];
    }
    default:
      return ["", "", ""];
  }
}

function soloCopy() {
  if (!state) return ["Setup", "Connect a micro:bit", "Plug in your board and connect it below."];
  const song = state.song || "";
  switch (state.phase) {
    case "waiting_devices":
      return [
        "Waiting for device · " + connectedCount() + " / 1",
        "Connect your micro:bit",
        "Plug your flashed micro:bit into this computer over USB. Song selection opens once it reaches the lobby.",
      ];
    case "lobby":
      return ["Lobby", "Pick a song", "Once confirmed, the chart loads onto your micro:bit and you ready up on the device."];
    case "readying":
      return ["Waiting for you", song, "Push right on your micro:bit when you’re ready. Pushing left cancels the round."];
    case "syncing":
      return ["Syncing", song, "Aligning your micro:bit with this computer’s clock."];
    case "countdown":
      return ["Get ready", song, "Music plays from this computer."];
    case "playing":
      return ["Now playing", song, ""];
    case "results": {
      const [player] = state.players;
      const heading = player.status !== "finished" ? "Didn’t finish"
        : player.miss === 0 ? "Full combo!" : number.format(player.score) + " points";
      return ["Results · " + song, heading, "Head back to the lobby to play again, or push left on your device."];
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
  document.title = (heading && state ? heading + " · " : "") + "Rhythm Hit " + MODE_NAME[mode];

  const back = $("back-lobby");
  back.hidden = state?.phase !== "results";
  back.disabled = returning;
  back.setAttribute("aria-busy", String(returning));

  const notice = $("notice");
  const message = state && ["lobby", "waiting_devices"].includes(state.phase)
    ? (isSolo() && SOLO_NOTICE[state.notice]) || NOTICE[state.notice] : "";
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

function renderRunSave() {
  const box = $("run-save");
  const show = accountReady && isSolo() && state?.phase === "results";
  box.hidden = !show;
  if (!show) return;
  box.dataset.kind = runSave?.kind || "";
  if (runSave) {
    box.replaceChildren(runSave.text);
  } else if (!currentUser()) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Sign up";
    button.addEventListener("click", () => openAuth("signup"));
    box.replaceChildren(button, " to save your next solo runs to the leaderboard.");
  } else {
    box.hidden = true;
  }
}

async function saveRun(pending, player) {
  runSave = { kind: "pending", text: "Saving your run…" };
  render();
  const id = await pending.id;
  try {
    if (!id) throw new Error();
    const result = await finishRun(id, player);
    const parts = ["Saved to the leaderboard"];
    if (result.rank) parts.push("Rank #" + result.rank);
    if (result.personal_best) parts.push("New personal best");
    runSave = { kind: "saved", text: parts.join(" · ") };
  } catch (error) {
    runSave = { kind: "error", text: error?.code === "login_required"
      ? "Log in again to save runs. This one wasn’t saved."
      : "This run couldn’t be saved to the leaderboard." };
  }
  render();
}

function trackRun(previous, latest) {
  if (latest.phase === "results" && previous !== "results" && run) {
    const pending = run;
    run = null;
    const [player] = latest.players;
    if (latest.mode === "solo" && player?.status === "finished") void saveRun(pending, player);
  } else if (["lobby", "waiting_devices"].includes(latest.phase) && previous !== latest.phase) {
    // A cancelled or finished round leaves nothing to record.
    run = null;
    runSave = null;
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
  link.dataset.online = serialUnsupported ? "unsupported" : String(online);
  $("connection-text").textContent = browserSetup
    ? (serialUnsupported ? "Use Chrome or Edge" : online ? "Web Serial ready" : "Browser setup")
    : (online ? "Host connected" : state ? "Reconnecting…" : "Connecting…");
  app.dataset.phase = state ? state.phase : "boot";
  app.dataset.mode = mode;
  renderMode();
  renderStage();
  renderRunSave();
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
      const song = state.songs[index];
      // Start the record before the round so its minimum play time holds.
      run = isSolo() && currentUser() && song?.id ? { id: startRun(song.id).catch(() => null) } : null;
      runSave = null;
      try {
        await browserHost.confirm(index);
      } catch (error) {
        run = null;
        throw error;
      }
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

$("back-lobby").addEventListener("click", async () => {
  if (returning || state?.phase !== "results") return;
  returning = true;
  render();
  try {
    if (browserHost) {
      browserHost.returnToLobby();
    } else {
      const response = await fetch("/lobby", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "null",
      });
      if (!response.ok) throw new Error();
    }
  } catch {
    // The next snapshot still shows results; the button stays available to retry.
  } finally {
    returning = false;
    render();
  }
});

/* ---------- Mode switch ---------- */

const modeBox = $("mode");
const modeToggle = $("mode-toggle");
const modeMenu = $("mode-menu");
const modeItems = [...modeMenu.querySelectorAll("[data-mode]")];

// Modes change only between rounds; results return to the lobby first.
function canSwitchMode() {
  return Boolean(browserHost) && !confirming && !returning &&
    ["waiting_devices", "lobby", "results"].includes(state?.phase);
}

function renderMode() {
  $("mode-label").textContent = MODE_NAME[mode];
  $("mode-static").textContent = MODE_NAME[mode];
  for (const item of modeItems) item.setAttribute("aria-checked", String(item.dataset.mode === mode));
  const allowed = canSwitchMode();
  modeToggle.disabled = !allowed;
  modeToggle.title = allowed || !browserHost ? "" : "Finish the round to switch modes";
  if (!allowed && !modeMenu.hidden) closeModeMenu(false);
}

function openModeMenu() {
  modeMenu.hidden = false;
  modeToggle.setAttribute("aria-expanded", "true");
  (modeItems.find((item) => item.dataset.mode === mode) ?? modeItems[0]).focus();
}

function closeModeMenu(restoreFocus = true) {
  if (modeMenu.hidden) return;
  modeMenu.hidden = true;
  modeToggle.setAttribute("aria-expanded", "false");
  if (restoreFocus) modeToggle.focus();
}

function chooseMode(next) {
  closeModeMenu();
  if (next === mode || !canSwitchMode()) return;
  try {
    browserHost.setMode(next);
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
    return;
  }
  mode = next;
  errorBox.hidden = true;
  try { localStorage.setItem(MODE_KEY, next); } catch { /* storage unavailable */ }
  render();
}

function setupModeSwitch() {
  modeBox.hidden = false;
  $("mode-static").hidden = true;
  modeToggle.addEventListener("click", () => (modeMenu.hidden ? openModeMenu() : closeModeMenu()));
  modeToggle.addEventListener("keydown", (event) => {
    if (["ArrowDown", "ArrowUp"].includes(event.key) && modeMenu.hidden && !modeToggle.disabled) {
      event.preventDefault();
      openModeMenu();
    }
  });
  for (const item of modeItems) item.addEventListener("click", () => chooseMode(item.dataset.mode));
  modeMenu.addEventListener("keydown", (event) => {
    const at = modeItems.indexOf(document.activeElement);
    if (event.key === "Escape") {
      event.preventDefault();
      closeModeMenu();
    } else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      const last = modeItems.length - 1;
      const next = event.key === "Home" ? 0 : event.key === "End" ? last
        : (at + (event.key === "ArrowDown" ? 1 : last)) % modeItems.length;
      modeItems[next].focus();
    } else if (event.key === "Tab") {
      closeModeMenu(false);
    }
  });
  document.addEventListener("pointerdown", (event) => {
    if (!modeBox.contains(event.target)) closeModeMenu(false);
  });
}

function displaySnapshot(latest, available) {
  if (latest.phase !== "lobby") {
    confirming = false;
    errorBox.hidden = true;
  }
  const previous = state?.phase;
  state = latest;
  online = available;
  trackRun(previous, latest);
  if (latest.mode) mode = latest.mode;
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
  mountAccountNav($("account"));
  onUserChange(() => render());
  loadAccount()
    .then(() => {
      if (!accountsEnabled()) throw new Error("accounts disabled");
      accountReady = true;
      render();
    })
    .catch(() => { $("account").hidden = true; });
  if (!serialUnsupported) setupModeSwitch();
  // Connect buttons could never work here; the stage explains what to do instead.
  if (serialUnsupported) browserSetup.querySelector(".pair-buttons").hidden = true;
  import("./browser/app.mjs")
    .then(({ startBrowserHost }) => startBrowserHost(displaySnapshot))
    .then((host) => {
      browserHost = host;
      // Restore the saved mode; the host always starts in versus.
      if (preferredMode !== host.mode) host.setMode(preferredMode);
      render();
    })
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
