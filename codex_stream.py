"""Decode Codex's pane stream into short-lived animation hints."""

import codecs
import re
import time


STATUS = re.compile(
    r"\b(Thinking|Working|Worked|Typing|Using\s+shell|Using\s+skill|"
    r"Viewed|Viewing|Ran|Running|Goal\s+active|Searched|Read|Edited|Wrote)\b"
    r"|\(no output\)",
    re.IGNORECASE,
)


def colors(params, fg, bg):
    if ":" in params:
        return fg, bg
    try:
        values = [int(v or "0") for v in params.split(";")] if params else [0]
    except ValueError:
        return fg, bg
    i = 0
    while i < len(values):
        v = values[i]
        if v == 0:
            fg = bg = None
        elif v == 39:
            fg = None
        elif v == 49:
            bg = None
        elif 30 <= v <= 37 or 90 <= v <= 97:
            fg = v
        elif 40 <= v <= 47 or 100 <= v <= 107:
            bg = v
        elif v in (38, 48) and i + 2 < len(values) and values[i + 1] == 5:
            color = f"256:{values[i + 2]}"
            if v == 38:
                fg = color
            else:
                bg = color
            i += 2
        elif v in (38, 48) and i + 4 < len(values) and values[i + 1] == 2:
            color = "rgb:" + ":".join(str(n) for n in values[i + 2:i + 5])
            if v == 38:
                fg = color
            else:
                bg = color
            i += 4
        i += 1
    return fg, bg


class CodexStream:
    def __init__(self):
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.mode = "text"
        self.csi = ""
        self.osc_esc = False
        self.tail = ""
        self.action = None
        self.fg = self.bg = None
        self.hint_fg = self.hint_bg = None
        self.updated = 0.0

    def feed(self, data):
        for c in self.decoder.decode(data):
            if self.mode == "text":
                if c == "\x1b":
                    self.mode = "escape"
                elif c.isprintable() or c in "\t\n\r":
                    text = self.tail + c
                    matches = list(STATUS.finditer(text))
                    match = matches[-1] if matches and matches[-1].end() == len(text) else None
                    if match:
                        cue = match.group(0).casefold()
                        self.action = (
                            "idle" if cue in {"worked", "(no output)"} else
                            "view" if cue in {"viewed", "viewing", "read", "searched"} else
                            "running" if cue in {"ran", "running"} else
                            "goal" if cue == "goal active" else
                            "working"
                        )
                        self.updated = time.monotonic()
                    self.tail = text[-64:]
                elif ord(c) < 32:
                    self.tail = (self.tail + " ")[-64:]
            elif self.mode == "escape":
                if c == "[":
                    self.mode, self.csi = "csi", ""
                elif c == "]":
                    self.mode, self.osc_esc = "osc", False
                else:
                    self.mode = "text"
            elif self.mode == "csi":
                if "@" <= c <= "~":
                    if c == "m":
                        old = self.fg, self.bg
                        self.fg, self.bg = colors(self.csi, self.fg, self.bg)
                        if self.fg is not None:
                            self.hint_fg = self.fg
                        if self.bg is not None:
                            self.hint_bg = self.bg
                        if old != (self.fg, self.bg):
                            self.updated = time.monotonic()
                    self.mode = "text"
                else:
                    self.csi += c
            elif c == "\x07" or (self.osc_esc and c == "\\"):
                self.mode, self.osc_esc = "text", False
            else:
                self.osc_esc = c == "\x1b"

    def snapshot(self):
        return self.action, {"fg": self.hint_fg, "bg": self.hint_bg}, self.updated
