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
`-t` if multiple matches remain. With no match, it creates an owned Codex and
Comeji session. `--no-codex` splits the current pane/window for autonomous
Comeji, or runs directly outside tmux; `-t pane` selects a pane explicitly.
Capture refuses to replace an existing `pipe-pane`, reporting the launcher
line number to stderr. In an existing session, quitting Comeji or interrupting
the launcher closes only its pane and capture pipe.

```text
if no_codex_target:
    scope = create_owned_tmux_scope()
    codex_pane, comeji_pane = create_two_panes(scope)
    start_in(comeji_pane, "exec python3 comeji.py")
    start_in(codex_pane):
        run_codex()
        close(scope)
    attach_to(scope)
else:
    target = explicit_target or find_codex_target()
    comeji_pane = split(target)
    capture_target_output(target)
    start_in(comeji_pane, "exec python3 comeji.py")
    on_comeji_exit_or_launcher_signal:
        close(comeji_pane)  # leave target pane and session alive
```

Keep the lifecycle out of `comeji.py`: curses returns on `q`, and the pane's
foreground process ends. The launcher owns cleanup of the larger tree.

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

- Commit the completed project, then add a few wacky ideas of Codex's choosing.
