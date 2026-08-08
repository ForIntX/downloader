#!/bin/sh
set -eu

APP_ID="com.forintx.VideoIndirici"
DATA_BASE="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_BASE="${XDG_CONFIG_HOME:-$HOME/.config}"
STATE_BASE="${XDG_STATE_HOME:-$HOME/.local/state}"
CACHE_BASE="${XDG_CACHE_HOME:-$HOME/.cache}"
APP_DATA="$DATA_BASE/video-indirici"
PURGE=0

case "${1:-}" in
    --purge) PURGE=1 ;;
    --help|-h) echo "Kullanım: ./uninstall.sh [--purge]"; exit 0 ;;
    "") ;;
    *) echo "Bilinmeyen seçenek: $1" >&2; exit 2 ;;
esac

rm -rf "$APP_DATA/app" "$APP_DATA/venv"
rm -f "$HOME/.local/bin/downloader" "$HOME/.local/bin/video-indirici"
rm -f "$DATA_BASE/applications/$APP_ID.desktop"
rm -f "$DATA_BASE/icons/hicolor/scalable/apps/$APP_ID.svg"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DATA_BASE/applications" || true

if [ "$PURGE" -eq 1 ]; then
    printf "Kuyruk, geçmiş, ayarlar ve loglar da silinsin mi? [e/H] "
    read -r answer
    case "$answer" in
        e|E|y|Y)
            rm -rf "$APP_DATA" "$CONFIG_BASE/video-indirici" "$STATE_BASE/video-indirici" "$CACHE_BASE/video-indirici"
            echo "Kullanıcı verileri silindi."
            ;;
        *) echo "Kullanıcı verileri korundu." ;;
    esac
fi

echo "Downloader kaldırıldı."
