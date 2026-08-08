from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from .utils import format_duration


@dataclass(frozen=True)
class MediaItem:
    path: Path
    title: str
    kind: str = "video"


class MediaPlayerWindow(Adw.Window):
    """Small, self-contained GTK media player used by the Linux application."""

    def __init__(
        self,
        parent: Adw.ApplicationWindow,
        items: list[MediaItem],
        start_index: int = 0,
        on_open_external: Callable[[Path], None] | None = None,
    ) -> None:
        if not items:
            raise ValueError("Oynatılacak dosya bulunamadı")
        super().__init__(transient_for=parent)
        self.set_default_size(820, 580)
        self.set_size_request(540, 400)

        self.items = items
        self.index = max(0, min(start_index, len(items) - 1))
        self.stream: Gtk.MediaFile | None = None
        self._on_open_external = on_open_external
        self._handled_end = False
        self._closed = False
        self._last_volume = 1.0
        self._tick_id = 0

        self._build_ui()
        self._install_shortcuts()
        self.connect("close-request", self._on_close_request)
        self._load_index(self.index)
        self._tick_id = GLib.timeout_add(200, self._refresh)

    @property
    def current_item(self) -> MediaItem:
        return self.items[self.index]

    def _build_ui(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)

        header = Adw.HeaderBar()
        self.header_title = Adw.WindowTitle(title="Downloader", subtitle="")
        header.set_title_widget(self.header_title)
        root.append(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_top(10)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_vexpand(True)
        root.append(content)

        self.media_stack = Gtk.Stack()
        self.media_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.media_stack.set_hexpand(True)
        self.media_stack.set_vexpand(True)

        self.picture = Gtk.Picture()
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.picture.set_hexpand(True)
        self.picture.set_vexpand(True)
        self.media_stack.add_named(self.picture, "video")

        audio_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        audio_box.set_valign(Gtk.Align.CENTER)
        audio_box.set_halign(Gtk.Align.CENTER)
        audio_icon = Gtk.Image.new_from_icon_name("audio-x-generic-symbolic")
        audio_icon.set_pixel_size(128)
        audio_box.append(audio_icon)
        self.audio_title = Gtk.Label()
        self.audio_title.set_wrap(True)
        self.audio_title.set_justify(Gtk.Justification.CENTER)
        self.audio_title.set_max_width_chars(52)
        self.audio_title.add_css_class("title-2")
        audio_box.append(self.audio_title)
        self.media_stack.add_named(audio_box, "audio")
        content.append(self.media_stack)

        self.status_label = Gtk.Label(xalign=0)
        self.status_label.set_wrap(True)
        self.status_label.add_css_class("error")
        self.status_label.set_visible(False)
        content.append(self.status_label)

        timeline = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.elapsed_label = Gtk.Label(label="0:00")
        self.position_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self.position_scale.set_draw_value(False)
        self.position_scale.set_hexpand(True)
        self.position_scale.set_sensitive(False)
        self.position_scale.connect("change-value", self._seek_changed)
        self.duration_label = Gtk.Label(label="0:00")
        timeline.append(self.elapsed_label)
        timeline.append(self.position_scale)
        timeline.append(self.duration_label)
        content.append(timeline)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        controls.set_halign(Gtk.Align.CENTER)
        self.previous_button = self._icon_button("media-skip-backward-symbolic", "Önceki dosya", self.previous)
        rewind = self._icon_button("media-seek-backward-symbolic", "10 saniye geri", lambda *_: self.seek_relative(-10))
        self.play_button = self._icon_button("media-playback-start-symbolic", "Oynat / duraklat", self.toggle_playback)
        self.play_button.add_css_class("suggested-action")
        forward = self._icon_button("media-seek-forward-symbolic", "10 saniye ileri", lambda *_: self.seek_relative(10))
        self.next_button = self._icon_button("media-skip-forward-symbolic", "Sonraki dosya", self.next)
        for button in (self.previous_button, rewind, self.play_button, forward, self.next_button):
            controls.append(button)
        content.append(controls)

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.mute_button = self._icon_button("audio-volume-high-symbolic", "Sesi kapat", self.toggle_mute)
        self.volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.05)
        self.volume_scale.set_draw_value(False)
        self.volume_scale.set_value(1)
        self.volume_scale.set_size_request(140, -1)
        self.volume_scale.connect("value-changed", self._volume_changed)
        bottom.append(self.mute_button)
        bottom.append(self.volume_scale)

        path_label = Gtk.Label(label="", xalign=0)
        path_label.set_ellipsize(3)
        path_label.set_hexpand(True)
        path_label.add_css_class("dim-label")
        self.path_label = path_label
        bottom.append(path_label)

        external = Gtk.Button(label="Harici Uygulamada Aç")
        external.set_tooltip_text("Dosyayı sistemin varsayılan uygulamasında aç")
        external.connect("clicked", self._open_external)
        bottom.append(external)
        content.append(bottom)

    @staticmethod
    def _icon_button(icon: str, tooltip: str, callback: Callable) -> Gtk.Button:
        button = Gtk.Button(icon_name=icon, tooltip_text=tooltip)
        button.connect("clicked", callback)
        return button

    def _install_shortcuts(self) -> None:
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._key_pressed)
        self.add_controller(controller)

    def _key_pressed(self, _controller, keyval: int, _keycode: int, state: Gdk.ModifierType) -> bool:
        if keyval == Gdk.KEY_space:
            self.toggle_playback()
            return True
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if keyval == Gdk.KEY_Left:
            if state & Gdk.ModifierType.CONTROL_MASK:
                self.previous()
            else:
                self.seek_relative(-10)
            return True
        if keyval == Gdk.KEY_Right:
            if state & Gdk.ModifierType.CONTROL_MASK:
                self.next()
            else:
                self.seek_relative(10)
            return True
        return False

    def _load_index(self, index: int) -> None:
        if self.stream:
            self.stream.pause()
        self.index = max(0, min(index, len(self.items) - 1))
        item = self.current_item
        self._handled_end = False
        self.status_label.set_visible(False)
        self.status_label.set_label("")
        self.position_scale.set_value(0)
        self.position_scale.set_sensitive(False)
        self.elapsed_label.set_label("0:00")
        self.duration_label.set_label("0:00")
        self.header_title.set_title(item.title or item.path.stem)
        self.header_title.set_subtitle(f"{self.index + 1} / {len(self.items)}")
        self.audio_title.set_label(item.title or item.path.stem)
        self.path_label.set_label(str(item.path))
        self.set_title(item.title or item.path.stem)
        self.previous_button.set_sensitive(self.index > 0)
        self.next_button.set_sensitive(self.index < len(self.items) - 1)

        if not item.path.is_file():
            self.stream = None
            self.picture.set_paintable(None)
            self.media_stack.set_visible_child_name("audio" if item.kind == "audio" else "video")
            self.status_label.set_label("Dosya bulunamadı. Taşınmış veya silinmiş olabilir.")
            self.status_label.set_visible(True)
            self.play_button.set_sensitive(False)
            return

        stream = Gtk.MediaFile.new_for_file(Gio.File.new_for_path(str(item.path)))
        stream.set_volume(self.volume_scale.get_value())
        self.stream = stream
        self.picture.set_paintable(stream)
        self.media_stack.set_visible_child_name("audio" if item.kind == "audio" else "video")
        self.play_button.set_sensitive(True)
        self.play_button.set_icon_name("media-playback-pause-symbolic")
        stream.play()

    def _refresh(self) -> bool:
        if self._closed:
            return False
        stream = self.stream
        if not stream:
            return True

        error = stream.get_error()
        if error:
            self.status_label.set_label(f"Dosya oynatılamadı: {error}")
            self.status_label.set_visible(True)
            self.play_button.set_sensitive(False)
        elif stream.is_prepared():
            self.status_label.set_visible(False)
            self.media_stack.set_visible_child_name("video" if stream.has_video() else "audio")

        duration_us = max(0, int(stream.get_duration()))
        timestamp_us = max(0, int(stream.get_timestamp()))
        duration = duration_us / 1_000_000
        timestamp = min(timestamp_us / 1_000_000, duration) if duration else timestamp_us / 1_000_000
        self.elapsed_label.set_label(format_duration(timestamp))
        self.duration_label.set_label(format_duration(duration))
        if duration > 0:
            self.position_scale.set_range(0, duration)
            self.position_scale.set_value(timestamp)
            self.position_scale.set_sensitive(stream.is_seekable())

        playing = stream.get_playing()
        self.play_button.set_icon_name(
            "media-playback-pause-symbolic" if playing else "media-playback-start-symbolic"
        )
        self.play_button.set_tooltip_text("Duraklat" if playing else "Oynat")

        if stream.get_ended() and not self._handled_end:
            self._handled_end = True
            if self.index < len(self.items) - 1:
                GLib.idle_add(self.next)
        return True

    def _seek_changed(self, _scale, _scroll_type, value: float) -> bool:
        if self.stream and self.stream.is_seekable():
            self.stream.seek(int(max(0, value) * 1_000_000))
            self._handled_end = False
        return False

    def seek_relative(self, seconds: float) -> None:
        stream = self.stream
        if not stream or not stream.is_seekable():
            return
        duration = max(0, int(stream.get_duration()))
        target = max(0, int(stream.get_timestamp()) + int(seconds * 1_000_000))
        if duration:
            target = min(target, duration)
        stream.seek(target)
        self._handled_end = False

    def toggle_playback(self, *_args) -> None:
        stream = self.stream
        if not stream:
            return
        if stream.get_ended():
            stream.seek(0)
            self._handled_end = False
        if stream.get_playing():
            stream.pause()
        else:
            stream.play()

    def previous(self, *_args) -> bool:
        if self.index > 0:
            self._load_index(self.index - 1)
        elif self.stream and self.stream.is_seekable():
            self.stream.seek(0)
        return False

    def next(self, *_args) -> bool:
        if self.index < len(self.items) - 1:
            self._load_index(self.index + 1)
        return False

    def _volume_changed(self, scale: Gtk.Scale) -> None:
        volume = scale.get_value()
        if volume > 0:
            self._last_volume = volume
        if self.stream:
            self.stream.set_volume(volume)
        self.mute_button.set_icon_name(
            "audio-volume-muted-symbolic" if volume <= 0 else "audio-volume-high-symbolic"
        )
        self.mute_button.set_tooltip_text("Sesi aç" if volume <= 0 else "Sesi kapat")

    def toggle_mute(self, *_args) -> None:
        if self.volume_scale.get_value() > 0:
            self._last_volume = self.volume_scale.get_value()
            self.volume_scale.set_value(0)
        else:
            self.volume_scale.set_value(max(0.05, self._last_volume))

    def _open_external(self, *_args) -> None:
        if self._on_open_external:
            self._on_open_external(self.current_item.path)

    def _on_close_request(self, *_args) -> bool:
        self._closed = True
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0
        if self.stream:
            self.stream.pause()
        self.picture.set_paintable(None)
        self.stream = None
        return False
