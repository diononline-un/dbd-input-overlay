#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin/dbd-input-overlay"
DESKTOP="$HOME/.local/share/applications/dbd-input-overlay.desktop"

if ! pacman -Q gtk4-layer-shell >/dev/null 2>&1 && [[ ! -d "$HOME/.local/opt/gtk4-layer-shell/usr/lib" ]]; then
    echo "gtk4-layer-shell fehlt. Zuerst ausführen:" >&2
    echo "  sudo pacman -S --needed gtk4-layer-shell python-gobject python-evdev" >&2
    exit 1
fi

mkdir -p "$(dirname "$BIN")" "$(dirname "$DESKTOP")"

cat > "$BIN" <<EOF
#!/usr/bin/env bash
exec "$ROOT/run.sh" "\$@"
EOF
chmod +x "$BIN"

cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=DBD Input Overlay
Comment=Transparentes Input-Overlay für Dead by Daylight
Exec=$BIN
Icon=input-keyboard
Terminal=false
Categories=Utility;
Actions=Stop;

[Desktop Action Stop]
Name=Overlay beenden
Exec=pkill -f dbd_overlay
EOF

echo "Installiert:"
echo "  $BIN"
echo "  $DESKTOP"
echo
echo "Start über Anwendungsmenü oder: dbd-input-overlay"
