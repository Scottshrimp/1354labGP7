"""Drive the existing micro:bit simulator from the Web Serial integration test."""

from bisect import bisect_right
import json
import sys

from test_multiplayer import Board


def simulate():
    notes = json.loads(sys.stdin.readline())
    timestamps = [stamp for stamp, _ in notes]
    boards = [Board((1 << 30) - 5000), Board(124251)]

    for board in boards:
        def hit(lane, device=board.board):
            elapsed = device["ticks_diff"](device["ticks_ms"](), device["sync_at"])
            index = bisect_right(timestamps, elapsed) - 1
            return index >= 0 and elapsed - timestamps[index] < 35 and lane == notes[index][1]

        board.button = hit

    try:
        for line in sys.stdin:
            now, frames, moves = json.loads(line)
            outgoing = []
            for board, frame, move in zip(boards, frames, moves):
                board.joy = lambda direction=move: direction
                if frame:
                    board.incoming.extend(frame.encode("ascii"))
                board.step(now)
                outgoing.append(board.outgoing.decode("ascii"))
                board.outgoing.clear()
            print(json.dumps(outgoing), flush=True)
    finally:
        for board in boards:
            board.close()


if __name__ == "__main__":
    simulate()
