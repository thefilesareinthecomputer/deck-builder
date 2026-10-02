#!/bin/bash
# Probe PowerPoint for Mac automation for deck-builder (spec section 9.2).
# Usage: ./probe_powerpoint.sh path/to/deck.pptx
# Unverified against current PowerPoint; that's what this is for. Report what it prints.
set -euo pipefail

DECK="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
APP="/Applications/Microsoft PowerPoint.app"
BOX="$HOME/Library/Containers/com.microsoft.Powerpoint/Data/deck-builder-probe"

[ -d "$APP" ] || { echo "FAIL: PowerPoint not found at $APP"; exit 2; }
mkdir -p "$BOX"
cp "$DECK" "$BOX/probe.pptx"
rm -f "$BOX/probe.pdf"

WAS_RUNNING=$(osascript -e 'application "Microsoft PowerPoint" is running')
echo "PowerPoint already running: $WAS_RUNNING"

START=$(date +%s)
set +e
OUT=$(osascript - "$BOX/probe.pptx" "$BOX/probe.pdf" "$WAS_RUNNING" <<'APPLESCRIPT' 2>&1
on run argv
	set deckPath to item 1 of argv
	set pdfPath to item 2 of argv
	set wasRunning to item 3 of argv
	tell application "Microsoft PowerPoint"
		open (POSIX file deckPath)
		set pres to active presentation
		set n to count of slides of pres
		save pres in ((POSIX file pdfPath) as text) as save as PDF
		close pres saving no
		if wasRunning is "false" then quit
	end tell
	return "slides=" & n
end run
APPLESCRIPT
)
RC=$?
set -e
echo "osascript exit=$RC elapsed=$(( $(date +%s) - START ))s"
echo "$OUT"

case "$OUT" in
  *-1743*) echo "FAIL: Automation permission denied. System Settings > Privacy & Security > Automation, allow this terminal to control Microsoft PowerPoint." ;;
esac

if [ -f "$BOX/probe.pdf" ]; then
  echo "PDF written: $BOX/probe.pdf"
  command -v pdfinfo >/dev/null && pdfinfo "$BOX/probe.pdf" | grep -E "Pages|Producer"
  command -v pdffonts >/dev/null && pdffonts "$BOX/probe.pdf"
else
  echo "FAIL: no PDF produced"
fi
echo "Also note: did any window or dialog appear on screen? (spec 9.2)"
