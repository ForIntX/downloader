#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
INSTALLED_VENV="${XDG_DATA_HOME:-$HOME/.local/share}/video-indirici/venv"

if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/.venv/bin/python"
    PATH="$SCRIPT_DIR/.venv/bin:$PATH"
elif [ -x "$INSTALLED_VENV/bin/python" ]; then
    PYTHON="$INSTALLED_VENV/bin/python"
    PATH="$INSTALLED_VENV/bin:$PATH"
else
    PYTHON=$(command -v python3 || true)
fi

if [ -z "${PYTHON:-}" ]; then
    echo "Hata: Python 3 bulunamadı. Önce ./install.sh çalıştırın." >&2
    exit 1
fi

if ! "$PYTHON" -c 'import gi; gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1"); from gi.repository import Gtk, Adw' >/dev/null 2>&1; then
    echo "Hata: GTK4/Libadwaita Python bağımlılıkları eksik. Önce ./install.sh çalıştırın." >&2
    exit 1
fi

if ! command -v yt-dlp >/dev/null 2>&1 || ! command -v ffmpeg >/dev/null 2>&1; then
    echo "Hata: yt-dlp veya FFmpeg bulunamadı. Önce ./install.sh çalıştırın." >&2
    exit 1
fi

export PATH
exec "$PYTHON" "$SCRIPT_DIR/app.py" "$@"
