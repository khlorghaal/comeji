#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
no_codex=0
target=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --no-codex) no_codex=1 ;;
        -t)
            [ "$#" -ge 2 ] || { printf 'usage: %s [--no-codex] [-t pane]\n' "$0" >&2; exit 2; }
            target=$2
            shift
            ;;
        *) printf 'usage: %s [--no-codex] [-t pane]\n' "$0" >&2; exit 2 ;;
    esac
    shift
done

if [ "$no_codex" -eq 1 ] && [ -z "${TMUX:-}" ] && [ -z "$target" ]; then
    exec python3 "$script_dir/comeji.py"
fi
command -v tmux >/dev/null 2>&1 || { printf '%s: tmux is required\n' "$0" >&2; exit 1; }

current_window=""
if [ -n "${TMUX_PANE:-}" ]; then
    current_window=$(tmux display-message -p -t "$TMUX_PANE" '#{window_id}' 2>/dev/null || true)
else
    current_pane=$(tmux display-message -p '#{pane_id}' 2>/dev/null || true)
    if [ -n "$current_pane" ]; then
        current_window=$(tmux display-message -p -t "$current_pane" '#{window_id}' 2>/dev/null || true)
    fi
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
    if [ -z "$target" ]; then target=${TMUX_PANE:-${current_pane:-}}; fi
    [ -n "$target" ] || { printf '%s: --no-codex needs a current pane or -t target\n' "$0" >&2; exit 2; }
    comeji_pane=$(tmux split-window -h -t "$target" -P -F '#{pane_id}' "exec python3 '$script_dir/comeji.py'")
    target_window=$(tmux display-message -p -t "$comeji_pane" '#{session_name}:#{window_index}')
    if [ -n "${TMUX:-}" ]; then tmux switch-client -t "$target_window"; else tmux attach-session -t "$target_window"; fi
    exit 0
fi

if [ -z "$target" ]; then
    if target=$(find_codex); then :
    else
        result=$?
        if [ "$result" -eq 2 ]; then
            printf '%s: multiple Codex panes; specify -t pane\n' "$0" >&2
            exit 2
        fi
        target=""
    fi
fi

if [ -n "$target" ]; then
    pipe_check_line=$LINENO
    if [ "$(tmux display-message -p -t "$target" '#{pane_pipe}')" = 1 ]; then
        printf '%s:%s: pane %s already has pipe-pane; leaving it untouched\n' "$0" "$pipe_check_line" "$target" >&2
        exit 1
    fi
    fifo="${TMPDIR:-/tmp}/comeji-$$.fifo"
    done_file="${TMPDIR:-/tmp}/comeji-$$.done"
    rm -f "$fifo" "$done_file"
    mkfifo "$fifo"
    target_window=$(tmux display-message -p -t "$target" '#{session_name}:#{window_index}')
    comeji_pane=$(tmux split-window -h -t "$target" -P -F '#{pane_id}')
    cleanup_target() {
        tmux pipe-pane -t "$target" 2>/dev/null || true
        tmux kill-pane -t "$comeji_pane" 2>/dev/null || true
        rm -f "$fifo" "$done_file"
    }
    trap cleanup_target EXIT
    trap 'exit 129' HUP
    trap 'exit 130' INT
    trap 'exit 143' TERM
    tmux pipe-pane -t "$target" "cat > '$fifo'"
    cmd="COMEJI_CODEX_FIFO='$fifo' python3 '$script_dir/comeji.py'; status=\$?; : > '$done_file'; tmux pipe-pane -t '$target' 2>/dev/null || :; rm -f '$fifo'; tmux kill-pane -t '$comeji_pane' 2>/dev/null || :; exit \$status"
    tmux send-keys -t "$comeji_pane" "$cmd" Enter
    if [ -n "${TMUX:-}" ]; then
        tmux switch-client -t "$target_window"
    else
        tmux attach-session -t "$target_window"
        exit 0
    fi
    while [ ! -e "$done_file" ]; do
        tmux display-message -p -t "$comeji_pane" '#{pane_id}' >/dev/null 2>&1 || break
        sleep 0.1
    done
    exit 0
fi

# No Codex pane: keep the owned-session fallback.
session="comeji-$$"
fifo="${TMPDIR:-/tmp}/comeji-$$.fifo"
rm -f "$fifo"
mkfifo "$fifo"
cleanup_owned() {
    if [ -n "${codex_pane:-}" ]; then tmux pipe-pane -t "$codex_pane" 2>/dev/null || true; fi
    tmux kill-session -t "$session" 2>/dev/null || true
    rm -f "$fifo"
}
trap cleanup_owned EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
codex_pane=$(tmux new-session -d -s "$session" -P -F '#{pane_id}')
comeji_pane=$(tmux split-window -h -t "$codex_pane" -P -F '#{pane_id}')
tmux pipe-pane -t "$codex_pane" "cat > '$fifo'"
tmux send-keys -t "$comeji_pane" "COMEJI_CODEX_FIFO='$fifo' exec python3 '$script_dir/comeji.py'" Enter
tmux send-keys -t "$codex_pane" "if codex; then status=0; else status=\$?; fi; tmux kill-session -t '$session' 2>/dev/null; exit \$status" Enter
if [ -n "${TMUX:-}" ]; then TMUX= tmux attach-session -t "$session"; else tmux attach-session -t "$session"; fi
