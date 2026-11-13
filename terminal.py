"""Curses input, colors, drawing and cleanup."""

import curses

TICK = 0.125
PALETTE = (
    (0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0),
    (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
)

def nearest_color(rgb):
    return min( range(8),
        key=lambda i: sum((rgb[c] - PALETTE[i][c]) ** 2 \
            for c in range(3)))


def indexed_rgb(index):
    if index < 16:
        base = PALETTE[index % 8]
        return tuple(min(255, v + (50 if index >= 8 else 0)) for v in base)
    if index < 232:
        levels = (0, 95, 135, 175, 215, 255)
        n = index - 16
        return levels[n // 36], levels[n // 6 % 6], levels[n % 6]
    grey = 8 + (index - 232) * 10
    return grey, grey, grey


def color_index(colors, palette_size):
    color = colors.get("fg")
    if isinstance(color, int):
        if 30 <= color <= 37:
            color -= 30
        elif 90 <= color <= 97:
            color = color - 90 + (8 if palette_size >= 256 else 0)
        else:
            color = None
    elif isinstance(color, str) and color.startswith("256:"):
        try:
            index = int(color[4:])
            if not 0 <= index < 256:
                color = None
            elif palette_size >= 256:
                color = index
            else:
                color = nearest_color(indexed_rgb(index))
        except ValueError:
            color = None
    elif isinstance(color, str) and color.startswith("rgb:"):
        try:
            rgb = tuple(map(int, color[4:].split(":")))
            if palette_size >= 256:
                color = min(range(256), key=lambda i: sum((rgb[c] - indexed_rgb(i)[c]) ** 2 for c in range(3)))
            else:
                color = nearest_color(rgb)
        except ValueError:
            color = None
    return color if isinstance(color, int) and 0 <= color < palette_size else None


def run(step):
    def loop(stdscr):
        try:
            curses.curs_set(0)
        except curses.error: pass
        stdscr.timeout(int(TICK * 1000))
        palette_size = 8
        current_color = None
        color_enabled = False
        try:
            if curses.has_colors():
                curses.start_color()
                palette_size = 256 if curses.COLORS >= 256 else 8
                try:
                    curses.use_default_colors()
                except curses.error:
                    pass
                curses.init_pair(1, 0, -1)
                color_enabled = True
        except curses.error:
            color_enabled = False

        while True:
            key = stdscr.getch()
            if key in (ord("q"), ord("Q"), 3):
                break
            height, width = stdscr.getmaxyx()
            frame, x, colors = step((height, width))
            stdscr.erase()
            if height and width:
                try:
                    color = color_index(colors, palette_size) if color_enabled else None
                    if color != current_color and color is not None:
                        curses.init_pair(1, color, -1)
                        current_color = color
                    attr = curses.color_pair(1) if color is not None else 0
                    rows = [frame[i:i + 12] for i in range(0, len(frame), 12)]
                    visible = min(height, len(rows))
                    for i, row in enumerate(rows[-visible:]):
                        y = height - visible + i
                        count = width - x - (1 if y == height - 1 else 0)
                        if count > 0:
                            stdscr.addnstr(y, x, row, count, attr)
                except curses.error: pass
            stdscr.refresh()
        stdscr.erase()
        stdscr.refresh()

    curses.wrapper(loop)
