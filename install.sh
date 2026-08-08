#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VERSION=$(sed -n '1p' "$SCRIPT_DIR/VERSION")
APP_ID="com.forintx.VideoIndirici"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/video-indirici/app"
VENV_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/video-indirici/venv"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
CHECK_ONLY=0
ASSUME_YES=0

for argument in "$@"; do
    case "$argument" in
        --check) CHECK_ONLY=1 ;;
        --yes|-y) ASSUME_YES=1 ;;
        --help|-h)
            echo "Kullanım / Usage: ./install.sh [--check] [--yes]"
            echo "  --check  Bağımlılıkları denetler, dosya değiştirmez / Checks dependencies without changing files"
            echo "  --yes    Eksik sistem paketlerinin kurulumunu onaylar / Approves installation of missing system packages"
            exit 0
            ;;
        *) echo "Bilinmeyen seçenek / Unknown option: $argument" >&2; exit 2 ;;
    esac
done

OS_RELEASE=${VIDEO_INDIRICI_OS_RELEASE:-/etc/os-release}
DISTRO_ID="unknown"
if [ -r "$OS_RELEASE" ]; then
    DISTRO_ID=$(sed -n 's/^ID=//p' "$OS_RELEASE" | tr -d '"' | head -n 1)
fi

missing=${VIDEO_INDIRICI_TEST_MISSING:-}
if [ -z "$missing" ]; then
    command -v python3 >/dev/null 2>&1 || missing="$missing python3"
    command -v ffmpeg >/dev/null 2>&1 || missing="$missing ffmpeg"
    command -v gst-inspect-1.0 >/dev/null 2>&1 || missing="$missing gstreamer-playback"
    if command -v python3 >/dev/null 2>&1; then
        python3 -c 'import gi; gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1"); from gi.repository import Gtk, Adw' >/dev/null 2>&1 || missing="$missing gtk4-libadwaita-python"
        python3 -m venv --help >/dev/null 2>&1 || missing="$missing python3-venv"
    fi
fi

echo "Downloader $VERSION bağımlılık kontrolü / dependency check"
if [ -z "$missing" ]; then
    echo "Tüm sistem bağımlılıkları hazır / All system dependencies are ready."
else
    echo "Eksik bileşenler / Missing components:$missing"
fi

case "$DISTRO_ID" in
    ubuntu|debian|linuxmint|pop)
        INSTALL_COMMAND="sudo apt-get install -y python3 python3-venv python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 ffmpeg gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-libav"
        ;;
    fedora|rhel|centos)
        INSTALL_COMMAND="sudo dnf install -y python3 python3-pip python3-gobject gtk4 libadwaita ffmpeg gstreamer1-plugins-base gstreamer1-plugins-good gstreamer1-plugins-bad-free gstreamer1-plugin-libav"
        ;;
    arch|manjaro|endeavouros)
        INSTALL_COMMAND="sudo pacman -S --needed python python-pip python-gobject gtk4 libadwaita ffmpeg gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-libav"
        ;;
    *) INSTALL_COMMAND="" ;;
esac

if [ "$CHECK_ONLY" -eq 1 ]; then
    if [ -n "$missing" ]; then
        [ -n "$INSTALL_COMMAND" ] && echo "Önerilen komut / Suggested command: $INSTALL_COMMAND"
        exit 1
    fi
    exit 0
fi

if [ -n "$missing" ]; then
    if [ -z "$INSTALL_COMMAND" ]; then
        echo "Dağıtım tanınmadı; eksikleri paket yöneticinizle kurun / Unknown distribution; install missing components with your package manager." >&2
        exit 1
    fi
    echo "Önerilen komut / Suggested command: $INSTALL_COMMAND"
    if [ "$ASSUME_YES" -eq 0 ]; then
        printf "Bu komut şimdi çalıştırılsın mı / Run this command now? [e/y/H/N] "
        read -r answer
        case "$answer" in e|E|y|Y) ;; *) echo "Kurulum iptal edildi / Installation cancelled."; exit 1 ;; esac
    fi
    sh -c "$INSTALL_COMMAND"
fi

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
python3 -m venv --system-site-packages "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip yt-dlp

rm -rf "$APP_DIR/video_indirici"
cp -R "$SCRIPT_DIR/video_indirici" "$APP_DIR/video_indirici"
cp "$SCRIPT_DIR/app.py" "$SCRIPT_DIR/start.sh" "$SCRIPT_DIR/VERSION" "$SCRIPT_DIR/LICENSE" "$SCRIPT_DIR/README.md" "$SCRIPT_DIR/README.tr.md" "$APP_DIR/"
cp "$SCRIPT_DIR/assets/$APP_ID.svg" "$ICON_DIR/$APP_ID.svg"

cat > "$BIN_DIR/downloader" <<EOF
#!/bin/sh
export PATH="$VENV_DIR/bin:\$PATH"
exec "$VENV_DIR/bin/python" "$APP_DIR/app.py" "\$@"
EOF
chmod +x "$BIN_DIR/downloader"
ln -sf "$BIN_DIR/downloader" "$BIN_DIR/video-indirici"

sed "s|^Exec=downloader$|Exec=$BIN_DIR/downloader|" \
    "$SCRIPT_DIR/assets/$APP_ID.desktop" > "$DESKTOP_DIR/$APP_ID.desktop"
chmod +x "$DESKTOP_DIR/$APP_ID.desktop"

rm -f "$DESKTOP_DIR/video-indirici.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESKTOP_DIR" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t "$(dirname "$(dirname "$ICON_DIR")")" >/dev/null 2>&1 || true

echo "Downloader $VERSION kuruldu / installed."
echo "Başlatmak için / To start: $BIN_DIR/downloader"
echo "Uygulama menüsündeki 'Downloader' simgesini de kullanabilirsiniz / You can also use the 'Downloader' icon in the application menu."
