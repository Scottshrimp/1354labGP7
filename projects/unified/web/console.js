const get = (id) => document.getElementById(id);
const form = get("pick-song");
const select = get("song");
const confirm = get("confirm");
const error = get("error");
const playerCards = [get("player-1"), get("player-2")];

const phases = {
  waiting_devices: ["雙人對局", "等待兩台 micro:bit", "兩台設備就緒後就可以選曲。"],
  lobby: ["控制台 · Ready", "選擇曲目", "確認後，由兩位玩家在各自的 micro:bit 按 Ready。"],
  readying: ["等待玩家 Ready", "", "譜面載入後，請在兩台 micro:bit 上各自向右確認。"],
  syncing: ["正在同步", "", "兩位玩家都已 Ready，正在對齊譜面和音樂。"],
  countdown: ["即將開場", "", ""],
  playing: ["對局進行中", "", ""],
  results: ["本局結算", "", "在兩台 micro:bit 上向左返回，即可重新選曲。"],
};
const statuses = {
  disconnected: "未連線",
  connecting: "連線中",
  idle: "設備就緒",
  loading: "載入譜面",
  waiting: "等待 Ready",
  ready: "已 Ready",
  playing: "演奏中",
  finished: "已完賽",
  failed: "譜面傳輸中斷",
  quit: "已退出",
  resetting: "返回大廳",
};
const notices = {
  sync_failed: "本局同步逾時。設備回到大廳後可重新選曲。",
  start_interrupted: "開場已取消。兩台設備就緒後可重新選曲。",
};
const scorer = new Intl.NumberFormat("zh-TW");
const time = (ms) => {
  const seconds = Math.floor(ms / 1000);
  return Math.floor(seconds / 60) + ":" + String(seconds % 60).padStart(2, "0");
};

let state;
let online = false;
let confirming = false;

function render() {
  const link = get("connection");
  link.dataset.online = String(online);
  link.textContent = online ? "Host 已連線" : "正在重新連線";
  if (!state) return;

  const [phase, title, description] = phases[state.phase];
  get("phase").textContent = phase;
  get("heading").textContent = title || state.song;
  get("hint").textContent = notices[state.notice] || description;
  get("hint").hidden = !get("hint").textContent;

  form.hidden = state.phase !== "lobby";
  if (!select.options.length) {
    select.replaceChildren(new Option("請選擇曲目", ""));
    for (const [index, song] of state.songs.entries()) {
      select.add(new Option(song, index));
    }
  }
  select.disabled = !online || confirming;
  confirm.disabled = !online || confirming || select.value === "";

  const timer = get("timer");
  timer.hidden = state.countdown === null;
  timer.textContent = state.countdown ?? "";
  get("timeline").hidden = !["countdown", "playing", "results"].includes(state.phase);
  get("progress").max = state.duration_ms || 1;
  get("progress").value = state.progress_ms;
  get("elapsed").textContent = time(state.progress_ms);
  get("duration").textContent = time(state.duration_ms);

  for (const [index, player] of state.players.entries()) {
    const card = playerCards[index];
    const showScore = state.phase === "playing" || state.phase === "results";
    const isResult = state.phase === "results" || player.status === "finished";
    const label = card.querySelector(".state");
    label.textContent = player.status === "disconnected" && player.score !== null
      ? "已掉線" : statuses[player.status];
    label.dataset.status = player.status;
    card.querySelector(".points").hidden = !showScore;
    card.querySelector(".score").textContent = scorer.format(player.score ?? 0);
    const stats = card.querySelector(".stats");
    stats.textContent = isResult && player.status !== "finished"
      ? "未完賽"
      : isResult ? "Miss " + scorer.format(player.miss) : "連擊 " + scorer.format(player.combo);
    stats.hidden = !showScore;
  }
}

select.addEventListener("change", render);
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (confirm.disabled || state.phase !== "lobby") return;
  confirming = true;
  error.hidden = true;
  render();
  try {
    const response = await fetch("/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Number(select.value)),
    });
    if (!response.ok) throw new Error("confirm");
  } catch {
    confirming = false;
    error.textContent = "無法確認曲目。請檢查兩台設備與音訊後再試。";
    error.hidden = false;
    render();
  }
});

const events = new EventSource("/events");
events.addEventListener("message", (event) => {
  const latest = JSON.parse(event.data);
  if (latest.phase !== "lobby") {
    confirming = false;
    error.hidden = true;
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
