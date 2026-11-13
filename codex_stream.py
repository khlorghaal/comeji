"""Decode Codex's pane stream into short-lived animation hints."""

import codecs
import re
import time


CUES = re.compile(
    r"\b(?P<goal>Goal\s*[:=]?\s*\[?(?:active|completed?|blocked|paused|budget[_ -]limit|usage[_ -]limit))\b|"
    r"\b(?P<effort>(?:reasoning\s+)?effort\s*[:=]?\s*(?P<level>minimal|low|medium|high|xhigh|max|ultra))\b|"
    r"\b(?P<context>context\s*[:=]?\s*(?P<used>100|[0-9]{1,2})\s*%(?:\s+(?P<left>left|remaining))?|"
    r"(?P<remaining>100|[0-9]{1,2})\s*%\s+(?:context\s+)?(?:left|remaining))|"
    r"\b(?P<status>Thinking|Working|Worked|Typing|Using\s+shell|Using\s+skill|"
    r"Viewed|Viewing|Ran|Running|Searched|Read|Edited|Wrote|Writing|"
    r"Compacting|Compacted|Waiting|Interrupted|Error|Failed|Retrying)\b|"
    r"(?P<empty>\(no output\))", re.IGNORECASE,
)


def cue_action(match):
    cue = " ".join(match.group().casefold().split())
    return {
        "thinking": "think", "typing": "write", "edited": "write",
        "wrote": "write", "writing": "write", "viewed": "view",
        "viewing": "view", "read": "view", "searched": "view",
        "ran": "running", "running": "running", "worked": "idle",
        "(no output)": "idle", "compacting": "compact", "compacted": "context_roomy",
        "waiting": "waiting", "interrupted": "waiting", "error": "blocked",
        "failed": "blocked", "retrying": "working",
    }.get(cue, "working")


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
        self.effects = {}

    def feed(self, data):
        for c in self.decoder.decode(data):
            if self.mode == "text":
                if c == "\x1b":
                    self.mode = "escape"
                elif c.isprintable() or c in "\t\n\r":
                    text = self.tail + c
                    matches = list(CUES.finditer(text))
                    if matches and matches[-1].end() == len(text):
                        match = matches[-1]
                        now = time.monotonic()
                        if match.group("context"):
                            remaining = match.group("remaining")
                            value = int(remaining or match.group("used"))
                            if remaining is None and match.group("left") is None:
                                value = 100 - value
                            self.effects["context"] = value
                        elif match.group("effort"):
                            self.effects["effort"] = match.group("level").casefold()
                        elif match.group("goal"):
                            status = re.sub(r"^goal\s*[:=]?\s*\[?", "", match.group(), flags=re.I)
                            self.effects["goal"] = status.casefold().replace("-", "_").replace(" ", "_")
                            self.effects["goal_at"] = now
                        else:
                            self.action = cue_action(match)
                            self.updated = now
                            if self.action == "blocked":
                                self.effects["error_at"] = now
                    self.tail = text[-192:]
                elif ord(c) < 32:
                    self.tail = (self.tail + " ")[-192:]
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
                        self.fg, self.bg = colors(self.csi, self.fg, self.bg)
                        if self.fg is not None:
                            self.hint_fg = self.fg
                        if self.bg is not None:
                            self.hint_bg = self.bg

                    self.mode = "text"
                else:
                    self.csi += c
            elif c == "\x07" or (self.osc_esc and c == "\\"):
                self.mode, self.osc_esc = "text", False
            else:
                self.osc_esc = c == "\x1b"

    def snapshot(self):
        return self.action, {"fg": self.hint_fg, "bg": self.hint_bg}, self.updated
