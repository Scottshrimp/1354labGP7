import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { readFile } from "node:fs/promises";
import { createInterface } from "node:readline";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { BoardSession, LineFramer, encode } from "../web/browser/rh1.mjs";
import { BrowserMatch } from "../web/browser/match.mjs";

const decoder = new TextDecoder();
const encoder = new TextEncoder();

test("uses bounded ASCII framing and discards overlong frames", () => {
  const framer = new LineFramer();
  assert.deepEqual([...framer.feed(encoder.encode("RH1,H"))], []);
  assert.deepEqual([...framer.feed(encoder.encode("B\r\n" + "x".repeat(61) + "RH1,HB\n"))], [["RH1", "HB"]]);
  assert.throws(() => encode("RH1", "not,one,field"), /Invalid RH1/);
});

test("browser host runs the real two-board game protocol", { timeout: 25000 }, async () => {
  const song = JSON.parse(await readFile(new URL("../dist/browser/starter-beat.json", import.meta.url), "utf-8"));
  const fixture = fileURLToPath(new URL("./browser_board_fixture.py", import.meta.url));
  const child = spawn(process.env.PYTHON || "python3", [fixture], { stdio: ["pipe", "pipe", "inherit"] });
  const exited = once(child, "exit");
  const replies = createInterface({ input: child.stdout })[Symbol.asyncIterator]();
  const boards = [new BoardSession("12345678"), new BoardSession("9abcdef0")];
  const scheduled = [];
  const match = new BrowserMatch([song], { schedule: (at) => scheduled.push(at), stop() {} });
  match.seats = boards;
  let now = 0;
  let dropGo = false;

  async function step(moves = [-1, -1]) {
    now += 5;
    const frames = boards.map((board, seat) => {
      if (!board.connected) return "";
      const frame = board.nextFrame(now);
      const line = frame ? decoder.decode(frame) : "";
      if (seat === 1 && dropGo && line.includes(",GO,")) {
        dropGo = false;
        return "";
      }
      return line;
    });
    child.stdin.write(JSON.stringify([now, frames, moves]) + "\n");
    const next = await replies.next();
    assert.equal(next.done, false, "micro:bit simulation exited");
    for (const [seat, data] of JSON.parse(next.value).entries()) {
      if (boards[seat].connected) boards[seat].feed(encoder.encode(data), now);
    }
    match.tick(now);
  }

  async function until(predicate, duration = 10000) {
    const end = now + duration;
    while (!predicate() && now < end) await step();
    assert.ok(predicate(), JSON.stringify(match.snapshot(now)));
  }

  async function move(direction, seats) {
    for (let i = 0; i < 10; i++) await step(seats.map((seat) => seat ? direction : -1));
    for (let i = 0; i < 10; i++) await step();
  }

  try {
    child.stdin.write(JSON.stringify(song.notes) + "\n");
    assert.throws(() => match.begin(0), /Both micro:bits/);
    await until(() => match.devicesReady);
    match.begin(0);
    await until(() => boards.every((board) => board.status === "waiting"));
    await move(1, [true, false]);
    assert.deepEqual(boards.map((board) => board.status), ["ready", "waiting"]);
    assert.deepEqual(scheduled, []);

    dropGo = true;
    await move(1, [false, true]);
    await until(() => match.phase === "playing");
    assert.deepEqual(scheduled, [match.startAt]);
    await until(() => match.phase === "results", song.duration + 3000);
    const fullScore = song.notes.length * 100;
    assert.deepEqual(match.snapshot(now).players.map((player) => [player.score, player.miss, player.best_combo]),
      [[fullScore, 0, song.notes.length], [fullScore, 0, song.notes.length]]);
    assert.equal(match.snapshot(now).progress_ms, song.duration);
    await move(3, [true, true]);
    await until(() => match.phase === "lobby");
    match.begin(0);
    await until(() => boards.every((board) => board.status === "waiting"));
    await move(1, [true, true]);
    await until(() => match.phase === "playing");
    boards[0].disconnect();
    await until(() => match.phase === "results", song.duration + 3000);
    const players = match.snapshot(now).players;
    assert.deepEqual(players.map((player) => player.status), ["disconnected", "finished"]);
    assert.equal(players[1].score, fullScore);
    assert.equal(scheduled.length, 2);
  } finally {
    child.stdin.end();
    assert.equal((await exited)[0], 0);
  }
});
