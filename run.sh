#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

LOCAL_LIB="$HOME/.local/opt/gtk4-layer-shell"
if ! ldconfig -p 2>/dev/null | grep -q 'libgtk4-layer-shell\.so'; then
    if [[ -d "$LOCAL_LIB/usr/lib" ]]; then
        export LD_LIBRARY_PATH="$LOCAL_LIB/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
        export GI_TYPELIB_PATH="$LOCAL_LIB/usr/lib/girepository-1.0${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"
    else
        echo "gtk4-layer-shell fehlt. Installieren mit: sudo pacman -S gtk4-layer-shell" >&2
        exit 1
    fi
fi

exec python3 -m dbd_overlay "$@"
