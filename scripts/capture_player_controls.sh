#!/usr/bin/env bash
# Capture genuine Forge client inputs and video, not a simulated HUD.
# All steps run with the actual HBCamera client focused under Xvfb.
set -euo pipefail
mkdir -p gameplay-capture
window="$(xdotool search --onlyvisible --name 'Minecraft' | head -n 1)"
test -n "$window"
# Openbox in headless Xvfb may not advertise _NET_ACTIVE_WINDOW.
# Activating the window is best-effort; focus and input can still work.
xdotool windowactivate "$window" 2> gameplay-capture/player-window-activate.log || true
xdotool windowfocus --sync "$window"
xdotool mousemove --window "$window" 630 360
printf 'window_id=%s focused=%s\\n' "$window" "$(xdotool getwindowfocus)" > gameplay-capture/player-window-focus.txt
# Record raw Xvfb display. Keep the interaction transcript with the video.
ffmpeg -hide_banner -loglevel warning -y -f x11grab -framerate 15 -video_size 1280x720 -i :99.0 -c:v libx264 -preset ultrafast -crf 28 -pix_fmt yuv420p gameplay-capture/minecraft-player-controls.mp4 > gameplay-capture/player-capture-ffmpeg.log 2>&1 &
record_pid=$!
cleanup() { kill -INT "$record_pid" 2>/dev/null || true; wait "$record_pid" || true; }
trap cleanup EXIT
log_action() { printf '%s INPUT %s\n' "$(date -u +%FT%TZ)" "$1" | tee -a gameplay-capture/player-control-inputs.log; }
sleep 3
log_action "default tactical camera screenshot"
scrot gameplay-capture/player-default-perspective.png
log_action "pan arrows"
xdotool keydown Right; sleep 2; xdotool keyup Right
xdotool keydown Up; sleep 2; xdotool keyup Up
log_action "zoom [ and ]"
xdotool key bracketleft; sleep 2; xdotool key bracketright; sleep 2
log_action "inspect I and cycle period"
xdotool key i; sleep 2; xdotool key period; sleep 2
log_action "test PageDown floor change then restore citizen follow with End"
xdotool key Next; sleep 2
# PageDown intentionally disables follow. Re-enable it and center the
# camera on the selected citizen before comparing roof screenshots.
xdotool key End; sleep 4
log_action "roof cutaway baseline (F8 off)"
sleep 3
scrot gameplay-capture/player-cutaway-off.png
log_action "enable experimental mesh cutaway F8"
xdotool key F8; sleep 5
scrot gameplay-capture/player-cutaway-on.png
log_action "restore roof mesh F8"
xdotool key F8; sleep 5
scrot gameplay-capture/player-cutaway-restored.png
log_action "switch to first person V"
xdotool key v; sleep 3
scrot gameplay-capture/player-first-person.png
log_action "return tactical V"
xdotool key v; sleep 3
scrot gameplay-capture/player-return-tactical.png
log_action "click citizen selection attempt at screen center"
xdotool mousemove --window "$window" 640 360 click 1
sleep 3
scrot gameplay-capture/player-after-click.png
log_action "restore original viewpoint Home"
xdotool key Home
sleep 2
cleanup
trap - EXIT
ffmpeg -hide_banner -v error -xerror -i gameplay-capture/minecraft-player-controls.mp4 -f null -
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 gameplay-capture/minecraft-player-controls.mp4
# Filmstrip from the genuine client recording for rapid visual review.
ffmpeg -hide_banner -v error -y -i gameplay-capture/minecraft-player-controls.mp4 \
  -vf 'fps=1/5,scale=320:180,tile=4x3' -frames:v 1 \
  gameplay-capture/player-controls-contact-sheet.png
test -s gameplay-capture/player-controls-contact-sheet.png
