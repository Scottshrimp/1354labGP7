const $ = (id) => document.getElementById(id);

const app = $("app");
const picker = $("picker");
const tracks = $("tracks");
const confirmButton = $("confirm");
const errorBox = $("error");
const countdown = $("countdown");
const count = $("count");
const lead = $("lead");

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const number = new Intl.NumberFormat("zh-TW");

const STEP = {
  boot: -1, waiting_devices: 0, lobby: 0, readying: 1,
  syncing: 2, countdown: 2, playing: 3, results: 4,
};

const STATUS = {
  disconnected: "未連線",
  connecting: "連線中",
  idle: "在大廳",
  loading: "載入譜面",
  waiting: "等待 Ready",
  ready: "已 Ready",
  playing: "演奏中",
  finished: "已完賽",
  failed: "譜面中斷",
  quit: "已退出",
  resetting: "返回大廳",
  dropped: "已掉線",
};

const IDLE = {
  disconnected: ["請用 USB 連接設備", "插上後會自動配對"],
  connecting: ["正在握手", "等待設備回應"],
  idle: ["已在大廳", "等待選曲"],
  loading: ["載入譜面", "請稍候片刻"],
  waiting: ["在設備上向右", "確認 Ready"],
  ready: ["已 Ready", "等待對手"],
  resetting: ["返回大廳中", "請稍候"],
  quit: ["已取消", "回到大廳後可重新開始"],
  failed: ["譜面傳輸中斷", "回到大廳後可重新開始"],
  dropped: ["設備已掉線", "重新插上後會自動配對"],
};

const NOTICE = {
  sync_failed: "上一局同步逾時，已取消。兩台設備回到大廳後可以重新選曲。",
  start_interrupted: "上一局在開場前被取消。兩台設備回到大廳後可以重新選曲。",
};

const ERRORS = {
  "Both devices must be in the lobby": "兩台設備都需要在大廳中才能開始。",
  "Unknown song": "找不到這首曲目，請重新選擇。",
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

const OUTCOME_LABEL = { win: "勝出", tie: "平手", dnf: "未完賽" };

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
      if (status === "idle" && phase === "waiting_devices") sub = "等待另一台設備";
      if (status === "idle" && phase === "results") sub = "等待對手返回";
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
    const combo = player.combo ?? 0;
    card.combo.textContent = number.format(combo);
    if (combo > card.lastCombo && !reduceMotion.matches) {
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
      strong.textContent = result[0] === "tie" ? "平手" : "無人完賽";
      lead.append(strong);
      return;
    }
    lead.dataset.leader = String(winner + 1);
    strong.textContent = "P" + (winner + 1) + " 勝";
    lead.append(strong, Math.abs(a - b) ? "+" + number.format(Math.abs(a - b)) : "");
    return;
  }
  if (a === b) {
    strong.textContent = "同分";
    lead.append(strong);
    return;
  }
  const leader = a > b ? 1 : 2;
  lead.dataset.leader = String(leader);
  strong.textContent = "+" + number.format(Math.abs(a - b));
  lead.append(strong, "P" + leader + " 領先");
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
      notes.textContent = number.format(info.notes) + " 音符";
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
    selection.textContent = "尚未選擇曲目";
  } else {
    const song = state.songs[index];
    const strong = document.createElement("strong");
    strong.textContent = typeof song === "string" ? song : song.title;
    selection.replaceChildren("已選：", strong);
  }
  confirmButton.disabled = locked || index === null;
  confirmButton.setAttribute("aria-busy", String(confirming));
  confirmButton.firstElementChild.textContent = confirming ? "載入中…" : "確認曲目";
}

/* ---------- Stage ---------- */

function connectedCount() {
  return state.players.filter((p) => p.status !== "disconnected" && p.status !== "connecting").length;
}

function stageCopy() {
  if (!state) {
    return ["連線中", "正在連接 host", "請先在終端機執行 multiplayer.py。"];
  }
  const song = state.song || "";
  switch (state.phase) {
    case "waiting_devices":
      return [
        "等待設備 · " + connectedCount() + " / 2",
        "連接兩台 micro:bit",
        "用 USB 將兩台刷好程式的設備接到這台電腦。兩台都進入聯機菜單後就能選曲。",
      ];
    case "lobby":
      return ["大廳", "選一首歌", "確認後，兩台設備會各自載入譜面，再由玩家在設備上 Ready。"];
    case "readying":
      return ["等待 Ready", song, "兩位玩家在各自的 micro:bit 上向右確認。任一方向左即取消本局。"];
    case "syncing":
      return ["同步中", song, "兩位玩家都已 Ready，正在對齊兩台設備的時鐘。"];
    case "countdown":
      return ["即將開始", song, "音樂由這台電腦播放。"];
    case "playing":
      return ["演奏中", song, ""];
    case "results": {
      const result = outcomes(state.players);
      const winner = result.indexOf("win");
      const heading = winner >= 0 ? "玩家 " + (winner + 1) + " 勝出"
        : result[0] === "tie" ? "平分秋色" : "本局無人完賽";
      return ["結算 · " + song, heading, "在兩台設備上向左返回大廳，就能開始下一局。"];
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
  document.title = (heading && state ? heading + " · " : "") + "Rhythm Hit 雙人對局";

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
  $("track-title").textContent = "歌曲進度";
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
  $("connection-text").textContent = online ? "Host 已連線" : state ? "正在重新連線" : "正在連線";
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
    const response = await fetch("/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(index),
    });
    if (!response.ok) {
      let detail = "";
      try { detail = await response.json(); } catch { /* non-JSON body */ }
      throw new Error(ERRORS[detail] || "無法確認曲目。請檢查兩台設備與音訊後再試。");
    }
  } catch (error) {
    confirming = false;
    errorBox.textContent = error instanceof TypeError ? "無法連接 host。" : error.message;
    errorBox.hidden = false;
    render();
  }
});

const events = new EventSource("/events");
events.addEventListener("message", (event) => {
  const latest = JSON.parse(event.data);
  if (latest.phase !== "lobby") {
    confirming = false;
    errorBox.hidden = true;
  }
  state = latest;
  online = true;
  render();
});
events.addEventListener("error", () => {
  online = false;
  confirming = false;
  render();
});

render();
