# Comeji

Install NumPy with `apt install python-numpy`, then run `python3 comeji.py`; `q`
quits. Animation frames are arranged left-to-right in 12-row strips in
`artwork.txt`; NumPy reshapes each strip into 12×12 frames.

`sh launch.sh` attaches to an existing Codex pane. Use
`--no-codex` for autonomous mode, or `-t pane` to choose a pane. Fresh Codex
activity and color hints expire back to autonomous behavior.

The launcher creates a nonmodal floating pane at the top right: 12×6 visible content
with a solid terminal-cell border. Codex keeps keyboard focus. Select Comeji's
pane and press `q` to close it. Context and goal effects overlay the cat; effort
changes its thinking tempo. Requires tmux's `new-pane` floating-pane support.
