# Comeji

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
`codex_stream.py` parses raw Codex bytes from the launcher's FIFO.
Run `python3 comeji.py` standalone or use `launch.sh` for tmux.

## Launcher and pane ownership

The launcher searches for Codex in the current window first, then across all
sessions. It prefers the active Codex pane in an attached session and asks for
`-t` if multiple matches remain. With no match, it reports an error; it never
starts Codex or sends keystrokes. `--no-codex` splits the current pane/window
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

## Codex-driven animation goals

The stream parser recognizes status phrases and ANSI foreground/background
colors. Comeji uses fresh hints, then returns to autonomous behavior. Captures
showed the status phrases and truecolor/256-color sequences. Distinct hints now
cover `Working`, `Viewed`/`Viewing`, `Ran`, `(no output)`, `Goal active`, and
related `Searched`, `Read`, `Edited`, `Wrote` and `Running` cues.

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
