#!/usr/bin/env python3
"""A small, self-contained terminal creature."""

import os
import random
import time
from pathlib import Path

import terminal
from codex_stream import CodexStream


ART_STRIDE = 12
ARTWORKS = {
    "idle": ("idle",),
    "walk": ("walk_a", "walk_b"),
    "sleep": ("sleep",),
    "view": ("view",),
    "goal": ("goal",),
    "working": ("walk_a", "walk_b"),
    "running": ("walk_b", "walk_a"),
}
ANIMATIONS = ARTWORKS
MOVE_INTERVAL = 0.22


def load_artwork():
    artworks = {}
    name, rows = None, []
    for line in (Path(__file__).with_name("artwork.txt")).read_text().splitlines() + [""]:
        if line and len(line) == ART_STRIDE and name:
            rows.append(line)
        elif line and len(line) != ART_STRIDE:
            if name or rows:
                raise ValueError("artwork blocks need exactly 12 rows of 12 cells")
            name = line
        elif not line and name:
            if len(rows) != ART_STRIDE:
                raise ValueError(f"{name}: expected 12 rows, got {len(rows)}")
            artworks[name] = "".join(rows).replace(".", " ")
            name, rows = None, []
    return artworks


ART = load_artwork()


def choose_action(now):
    action = random.choices(
        ("walk", "idle", "view", "sleep"), weights=
        (     6,      2,      1,       1))[0]
    return action, now + random.uniform(*({
        "walk":  (3.0, 7.0),
        "idle":  (1.0, 3.0),
        "view":  (1.0, 2.5),
        "sleep": (2.5, 5.0),
    }[action]))

def main():
    x = 0
    direction = 1
    action = "idle"
    deadline = move_at = time.monotonic()
    fifo_path = os.environ.get("COMEJI_CODEX_FIFO")
    fifo_fd = os.open(fifo_path, os.O_RDWR | os.O_NONBLOCK) if fifo_path else None
    stream = CodexStream()

    def step(size):
        nonlocal x, direction, action, deadline, move_at
        now = time.monotonic()
        if now >= deadline:
            action, deadline = choose_action(now)
            move_at = now

        if fifo_fd is not None:
            try:
                while data := os.read(fifo_fd, 65536):
                    stream.feed(data)
            except BlockingIOError:
                pass

        hinted_action, colors, hint_time = stream.snapshot()
        fresh_hint = now - hint_time < 2.5
        shown_action = hinted_action if fresh_hint and hinted_action in ANIMATIONS else action

        colors = colors if fresh_hint else {}
        _, width = size
        max_x = max(0, width - ART_STRIDE)
        x = min(max(x, 0), max_x)

        if shown_action in {"walk", "working", "running", "goal"} and now >= move_at and max_x:
            x += direction
            if x <= 0 or x >= max_x:
                x = min(max(x, 0), max_x)
                direction *= -1
                action = "idle"
                deadline = now + random.uniform(0.3, 0.8)
            move_at = now + (MOVE_INTERVAL / 2 if shown_action == "running" else MOVE_INTERVAL)

        frames = ARTWORKS[shown_action]
        frame = ART[frames[int(now / 0.35) % len(frames)]]
        return frame, x, colors

    try:
        terminal.run(step)
    finally:
        if fifo_fd is not None:
            os.close(fifo_fd)


if __name__ == "__main__":
    main()
