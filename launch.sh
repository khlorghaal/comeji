#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# Run as the companion pane's command, independent of the user's default shell.
# This process owns its capture pipe and temporary directory.
if [ "${1:-}" = --run-pane ]; then
    target=$2
    capture_dir=$3
    (
        previous=""
        while size=$(tmux display-message -p -t "$TMUX_PANE" '#{window_width}x#{window_height}' 2>/dev/null); do
            if [ "$size" != "$previous" ]; then
                tmux move-pane -t "$TMUX_PANE" -P top-right 2>/dev/null || break
                previous=$size
            fi
            sleep 1
        done
    ) &
    watcher=$!
    cleanup() {
        kill "$watcher" 2>/dev/null || true
        if [ -n "$capture_dir" ]; then
            tmux pipe-pane -t "$target" 2>/dev/null || true
            rm -f "$capture_dir/output"
            rmdir "$capture_dir" 2>/dev/null || true
        fi
    }
    trap cleanup EXIT
    trap 'exit 129' HUP
    trap 'exit 130' INT
    trap 'exit 143' TERM
    if [ -n "$capture_dir" ]; then export COMEJI_CODEX_FIFO="$capture_dir/output"; fi
    COMEJI_BORDER=1 python3 "$script_dir/comeji.py"
    exit "$?"
fi

quote() {
    printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

usage() {
    printf 'usage: %s [--no-codex] [-t pane]\n' "$0" >&2
    exit 2
}

no_codex=0
target=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --no-codex) no_codex=1 ;;
        --popup) : ;;  # Accept the former flag; floating is now the default.
        -t)
            [ "$#" -ge 2 ] || usage
            target=$2
            shift
            ;;
        *) usage ;;
    esac
    shift
done

if [ "$no_codex" -eq 1 ] && [ -z "${TMUX:-}" ] && [ -z "$target" ]; then
    exec python3 "$script_dir/comeji.py"
fi
command -v tmux >/dev/null 2>&1 || { printf '%s: tmux is required\n' "$0" >&2; exit 1; }

current_pane=${TMUX_PANE:-}
current_window=""
if [ -n "$current_pane" ]; then
    current_window=$(tmux display-message -p -t "$current_pane" '#{window_id}' 2>/dev/null || true)
fi

find_codex() {
    current=""
    current_active=""
    attached_active=""
    all=""
    while IFS='|' read -r pane cmd active attached window; do
        case "$cmd" in codex|Codex|CODEX) ;; *) continue ;; esac
        all="$all $pane"
        if [ -n "$current_window" ] && [ "$window" = "$current_window" ]; then
            current="$current $pane"
            if [ "$active" = 1 ]; then current_active="$current_active $pane"; fi
        fi
        if [ "$active" = 1 ] && [ "$attached" -gt 0 ] 2>/dev/null; then
            attached_active="$attached_active $pane"
        fi
    done <<EOF_PANES
$(tmux list-panes -a -F '#{pane_id}|#{pane_current_command}|#{pane_active}|#{session_attached}|#{window_id}' 2>/dev/null || true)
EOF_PANES
    set -- $current
    if [ "$#" -eq 1 ]; then printf '%s\n' "$1"; return 0; fi
    if [ "$#" -gt 1 ]; then
        set -- $current_active
        if [ "$#" -eq 1 ]; then printf '%s\n' "$1"; return 0; fi
        return 2
    fi
    set -- $attached_active
    if [ "$#" -eq 1 ]; then printf '%s\n' "$1"; return 0; fi
    set -- $all
    if [ "$#" -eq 1 ]; then printf '%s\n' "$1"; return 0; fi
    if [ "$#" -gt 1 ]; then return 2; fi
    return 1
}

if [ "$no_codex" -eq 1 ]; then
    target=${target:-$current_pane}
    [ -n "$target" ] || { printf '%s: --no-codex needs a current pane or -t target\n' "$0" >&2; exit 2; }
elif [ -z "$target" ]; then
    if target=$(find_codex); then :
    else
        result=$?
        if [ "$result" -eq 2 ]; then
            printf '%s: multiple Codex panes; specify -t pane\n' "$0" >&2
        else
            printf '%s: no Codex pane found; specify -t pane or use --no-codex\n' "$0" >&2
        fi
        exit 2
    fi
fi

# Resolve once to immutable IDs before creating or cleaning up anything.
target=$(tmux display-message -p -t "$target" '#{pane_id}')
case "$target" in
    %*[!0-9]*|%|'') printf '%s: invalid pane ID\n' "$0" >&2; exit 2 ;;
    %*) ;;
    *) printf '%s: invalid pane ID\n' "$0" >&2; exit 2 ;;
esac
target_window=$(tmux display-message -p -t "$target" '#{window_id}')


capture_dir=""
comeji_pane=""
pipe_started=0
cleanup_setup() {
    if [ "$pipe_started" -eq 1 ]; then tmux pipe-pane -t "$target" 2>/dev/null || true; fi
    if [ -n "$comeji_pane" ]; then tmux kill-pane -t "$comeji_pane" 2>/dev/null || true; fi
    if [ -n "$capture_dir" ]; then
        rm -f "$capture_dir/output"
        rmdir "$capture_dir" 2>/dev/null || true
    fi
}
trap cleanup_setup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

if [ "$no_codex" -eq 1 ]; then
    pane_command="exec sh $(quote "$script_dir/launch.sh") --run-pane $(quote "$target") ''"
else
    # POSIX sh need not provide LINENO (and set -u makes using it fatal).
    pipe_check_line=$(awk '/^[ ]*if .*pane_pipe/ {print NR; exit}' "$script_dir/launch.sh")
    if [ "$(tmux display-message -p -t "$target" '#{pane_pipe}')" = 1 ]; then
        printf '%s:%s: pane %s already has pipe-pane; leaving it untouched\n' "$0" "$pipe_check_line" "$target" >&2
        exit 1
    fi
    capture_dir=$(mktemp -d "${TMPDIR:-/tmp}/comeji.XXXXXXXX")
    mkfifo "$capture_dir/output"
    tmux pipe-pane -O -t "$target" "exec cat > $(quote "$capture_dir/output")"
    pipe_started=1
    pane_command="exec sh $(quote "$script_dir/launch.sh") --run-pane $(quote "$target") $(quote "$capture_dir")"
fi

# A floating pane remains visible while the target retains keyboard focus.
comeji_pane=$(sh "$script_dir/../../tools/tmux-pane" floating "$target" "$pane_command")
# The companion now owns capture cleanup. Returning lets Codex launch us safely.
trap - EXIT HUP INT TERM
if [ -z "${TMUX:-}" ]; then
    tmux attach-session -t "$target_window"
fi
