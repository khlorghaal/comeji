# Comeji

## Todo

- Extract the reusable tmux launch method into a standalone Unix-style tool;
  have Comeji use it. Share it with lllx, which needs a regular right-hand pane.

Make a little character that lives in a tmux pane. It should be pleasant to
watch even when nothing else is happening: walking, pausing, looking around and
occasionally sleeping. This is a terminal program, not a desktop overlay.

## First version

- Draw a 12×12 character from text grids in `artwork.txt`; select animation
  elements by index and address cells with a stride of 12.
- It walks along the bottom of its pane, turns at the edges, idles and sometimes
  sleeps. Randomly vary the duration of actions so it doesn't feel mechanical.
- `q` quits. It runs in a regular terminal as well as tmux. Resizing the pane
  keeps the character visible, including when the pane is too small for a frame.
- No configuration system, networking, asset format, package manager or
  external runtime dependencies. The optional tmux launcher can pass Codex
  hints; autonomous life must stand on its own.

## Architecture

`comeji.py` owns autonomous behavior and consumes optional hints.
`terminal.py` owns curses input, grid drawing, cleanup and color conversion.
`effects.py` composites status marks independently of the character action.
`codex_stream.py` parses raw Codex bytes from the launcher's FIFO.
Run `python3 comeji.py` standalone or use `launch.sh` for tmux.

## Launcher and pane ownership

- Floating view: `new-pane -d -A` creates 12×6 content with a left and bottom
  line; `move-pane -P top-right` places it. The target retains focus and remains
  interactive. Borders are terminal cells rather than pixel units.

The launcher searches for Codex in the current window first, then across all
sessions. It prefers the active Codex pane in an attached session and asks for
`-t` if multiple matches remain. With no match, it reports an error; it never
starts Codex or sends keystrokes. `--no-codex` floats in the current window
for autonomous Comeji, or runs directly outside tmux; `-t` selects any pane.
Capture refuses to replace an existing `pipe-pane`, reporting the launcher
line number to stderr. Commands start directly in the new pane, independent
of the user's interactive shell. Inside tmux the launcher returns immediately
and preserves focus; the companion process owns cleanup of its capture.
Quitting Comeji closes its own pane and capture, leaving the target alive.
Setup failures clean up only resources created by that invocation. No launcher
path kills a session or server.

## Implementation status

The standalone TUI, launcher and Codex hint path are implemented. Idle, walking,
view, goal and sleep use text-grid artwork. Preserve autonomous behavior when
no Codex stream is available.

## Character and Codex effects

The character is a sparse outlined cat with blinking eyes, moving tail, and
four-frame idle, sleep, view, thinking, pondering, writing, compaction, waiting
and blocked actions. Walking retains alternating foot poses. Status effects
compose onto the same 12×12 grid without replacing the underlying action:

- `effort low|medium` changes thinking tempo; `high|xhigh|max|ultra` selects
  intense pondering. Effort persists until the next label.
- `context N%` means used; `context N% left` or `N% [context] left` means
  remaining. A persistent six-segment gauge shows consumption; at most 20%
  remaining adds a blinking warning.
- `Goal [active|complete|blocked|paused|budget_limit|usage_limit]` adds a moving
  star, four-second confetti, blocked marker, pause bars, or limit marks.
  Brackets are optional. Goal status persists independently of tool activity.
- `Typing`, `Writing`, `Edited`, `Wrote` → writing; `Compacting` → squeezing;
  `Waiting`/`Interrupted` → waiting; `Error`/`Failed` → blocked with a brief
  flashing marker; `Retrying` → working. View/run/working cues remain.

These are text heuristics, including matches in ordinary output; they do not
read Codex's internal state. Supported effort/context spellings do not imply
that every Codex version emits them. Inactive action hints expire back to
random autonomous behavior; metadata effects remain until replaced.

## Verification

- All referenced artwork grids are 12×12; redesigned actions and layered
  effects were inspected together as rendered images.
- Parser checks covered every chunk size for effort, used/remaining context,
  and goal labels, plus ANSI-separated activity and persistent metadata.
- Effect checks covered layering and celebration expiry. Standalone curses
  started and quit through PTYs at 12×12, 5×6 and 20×40.
- Earlier mocked launcher checks covered pane, popup, autonomous mode, occupied
  capture, no target, and setup failure cleanup.
- Floating-pane behavior is verified on a private explicit tmux socket:
  placement, retained target focus, drawing and cleanup before the resize.
  No session or server kill commands are used; host tmux remains untouched.

## After implementation

The initial implementation is committed as `a50503c`; the ideas below are
speculative possibilities, not current implementation requirements.

## Implementation lessons

- Terminal output capture and pane lifetime are separate resources; cleanup
  must follow ownership boundaries.
- Keep tool-specific stream decoding at the input edge, and translate it into
  small, expiring behavior hints for the character.
- Fixed-grid artwork depends on one stride being honored by loading, movement,
  clipping and drawing.
- Simulations can verify launcher decisions, while PTYs verify curses behavior;
  neither justifies probing a shared terminal multiplexer as though it were
  isolated.

## Wacky idea jar

- Give Comeji occasional zoomies: sprint to an edge, overshoot in spirit, then
  turn back with a tiny pause as if embarrassed.
- Let it inspect the stream: swivel its ears toward fresh output, then look back
  at the user when a tool finishes.
- During sleep, let a small `z` drift upward and vanish; some nights it dreams
  in punctuation from the latest tool output.
