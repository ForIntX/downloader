from __future__ import annotations

import copy
import os
import queue
import shutil
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from .constants import (
    APP_ID,
    APP_NAME,
    APP_VERSION,
    APP_VERSION_LABEL,
    COOKIE_BROWSERS,
    DEFAULT_CONFIG,
    FRAGMENT_OPTIONS,
    LOG_FILE,
    PARALLEL_OPTIONS,
    SPEED_LIMITS,
    SUB_LANGS,
    WEBSITE_URL,
)
from .downloader import DownloadEngine, MetadataScanner
from .i18n import set_language, tr, translate_widget_tree
from .models import (
    PRESETS,
    DownloadEvent,
    DownloadJob,
    DownloadStatus,
    HistoryEntry,
    PlaylistEntry,
)
from .persistence import LOGGER, PersistenceManager
from .player import MediaItem, MediaPlayerWindow
from .ui_models import BoundMarquee, HistoryObject, JobObject, PlaylistObject
from .utils import format_duration, is_playlist_url, is_valid_url, path_uri


STATUS_LABELS = {
    DownloadStatus.PENDING.value: "Bekliyor",
    DownloadStatus.DOWNLOADING.value: "İndiriliyor",
    DownloadStatus.PAUSED.value: "Duraklatıldı",
    DownloadStatus.COMPLETED.value: "Tamamlandı",
    DownloadStatus.ERROR.value: "Hata",
    DownloadStatus.CANCELLED.value: "İptal",
}


class VideoIndiriciApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self) -> None:
        window = self.props.active_window
        if window is None:
            window = MainWindow(self)
        window.present()


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, application: VideoIndiriciApplication) -> None:
        super().__init__(application=application, title=f"{APP_NAME} {APP_VERSION_LABEL}")
        self.set_default_size(1040, 760)
        self.set_size_request(820, 640)

        self.storage = PersistenceManager()
        self.config = self.storage.load_config()
        set_language(str(self.config.get("language", "tr")))
        self.history = self.storage.load_history()
        restored_jobs = self.storage.load_queue()
        self.events: queue.Queue[DownloadEvent] = queue.Queue()
        self.engine = DownloadEngine(self.events.put, self._config_snapshot)
        self.engine.set_jobs(restored_jobs)
        self.scanner = MetadataScanner(self.events.put, self._config_snapshot)
        self._closing = False
        self._cleaned = False
        self._metadata_token = ""
        self._metadata_scanning = False
        self._playlist_title = "Oynatma Listesi"
        self._playlist_uploader = ""
        self._video_info: dict[str, Any] | None = None
        self._thumbnail_token = ""
        self._clipboard_text = ""
        self._recorded_completions: set[str] = set()

        self.playlist_store = Gio.ListStore.new(PlaylistObject)
        self.playlist_query = ""
        self.playlist_filter = Gtk.CustomFilter.new(self._playlist_filter_func)
        self.playlist_filtered = Gtk.FilterListModel.new(self.playlist_store, self.playlist_filter)
        self.playlist_selection_model = Gtk.NoSelection.new(self.playlist_filtered)

        self.queue_store = Gio.ListStore.new(JobObject)
        self.queue_selection_model = Gtk.NoSelection.new(self.queue_store)
        self.history_store = Gio.ListStore.new(HistoryObject)
        self._history_filter_mode = "all"
        self.history_filter = Gtk.CustomFilter.new(self._history_filter_func)
        self.history_filtered = Gtk.FilterListModel.new(self.history_store, self.history_filter)
        self.history_selection_model = Gtk.NoSelection.new(self.history_filtered)
        self._player_windows: list[MediaPlayerWindow] = []

        self._install_css()
        self._build_ui()
        self._translate_windows()
        self._populate_queue(restored_jobs)
        self._populate_history()
        self.connect("close-request", self._on_close_request)
        GLib.timeout_add(50, self._drain_events)
        GLib.timeout_add(250, self._translate_windows)
        if self.config.get("clipboard", True):
            GLib.timeout_add(1000, self._check_clipboard)
        GLib.idle_add(self._check_dependencies)

    def _config_snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.config)

    def _translate_windows(self) -> bool:
        if self._cleaned:
            return False
        windows = Gtk.Window.get_toplevels()
        for index in range(windows.get_n_items()):
            window = windows.get_item(index)
            if window:
                translate_widget_tree(window)
        return True

    def _install_css(self) -> None:
        css = b"""
        .page { padding: 18px; }
        .card { border-radius: 14px; padding: 14px; background: alpha(@card_bg_color, .95); border: 1px solid alpha(@borders, .45); }
        .section-title { font-size: 15px; font-weight: 700; }
        .video-title { font-size: 14px; font-weight: 650; }
        .video-meta { font-size: 12px; opacity: .72; }
        .queue-row, .playlist-row, .history-row { padding: 9px 10px; border-bottom: 1px solid alpha(@borders, .3); }
        .status-badge { padding: 3px 8px; border-radius: 7px; font-size: 11px; font-weight: 650; }
        .status-badge.downloading { background: alpha(@accent_color, .18); color: @accent_color; }
        .status-badge.completed { background: alpha(@success_color, .16); color: @success_color; }
        .status-badge.error { background: alpha(@error_color, .16); color: @error_color; }
        .status-badge.paused { background: alpha(@warning_color, .18); color: @warning_color; }
        .muted { opacity: .58; }
        .big-button { min-height: 42px; font-weight: 700; }
        .description-box { padding: 12px; border-radius: 10px; background: alpha(@view_bg_color, .55); }
        .description-toggle { padding: 8px 10px; font-weight: 650; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _build_ui(self) -> None:
        self.toast_overlay = Adw.ToastOverlay()
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(root)
        self.set_content(self.toast_overlay)

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=APP_NAME, subtitle=APP_VERSION_LABEL))
        menu = Gio.Menu()
        menu.append("Ayarlar", "win.settings")
        menu.append("yt-dlp güncelle", "win.update_ytdlp")
        menu.append("Log klasörünü aç", "win.open_logs")
        menu.append("Hakkında", "win.about")
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        header.pack_end(menu_button)
        root.append(header)

        for name, callback in (
            ("settings", self._action_settings),
            ("update_ytdlp", self._action_update_ytdlp),
            ("open_logs", self._action_open_logs),
            ("about", self._action_about),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tab_box.set_halign(Gtk.Align.CENTER)
        tab_box.set_margin_top(8)
        tab_box.set_margin_bottom(8)
        self.tab_buttons: dict[str, Gtk.ToggleButton] = {}
        group: Gtk.ToggleButton | None = None
        for key, label in (("download", "İndir"), ("queue", "Kuyruk"), ("history", "Geçmiş")):
            button = Gtk.ToggleButton(label=label)
            if group:
                button.set_group(group)
            else:
                group = button
                button.set_active(True)
            button.connect("toggled", self._switch_tab, key)
            tab_box.append(button)
            self.tab_buttons[key] = button
        root.append(tab_box)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_vexpand(True)
        root.append(self.stack)
        self.stack.add_named(self._build_download_page(), "download")
        self.stack.add_named(self._build_queue_page(), "queue")
        self.stack.add_named(self._build_history_page(), "history")

    def _build_download_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.add_css_class("page")

        url_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        url_card.add_css_class("card")
        url_card.append(self._label("Video veya playlist URL'si", "section-title"))
        url_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.url_entry = Gtk.Entry(placeholder_text="https://www.youtube.com/watch?v=...")
        self.url_entry.set_hexpand(True)
        self.url_entry.connect("activate", lambda *_: self._fetch_metadata())
        self.url_entry.connect("changed", self._url_changed)
        paste_button = Gtk.Button(label="Yapıştır")
        paste_button.connect("clicked", self._paste_url)
        fetch_button = Gtk.Button(label="Bilgi Getir")
        fetch_button.add_css_class("suggested-action")
        fetch_button.connect("clicked", lambda *_: self._fetch_metadata())
        url_row.append(self.url_entry)
        url_row.append(paste_button)
        url_row.append(fetch_button)
        url_card.append(url_row)

        mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.video_mode = Gtk.ToggleButton(label="Video")
        self.playlist_mode = Gtk.ToggleButton(label="Playlist")
        self.playlist_mode.set_group(self.video_mode)
        self.video_mode.set_active(True)
        self.video_mode.connect("toggled", self._download_mode_changed)
        self.playlist_mode.connect("toggled", self._download_mode_changed)
        mode_row.append(self.video_mode)
        mode_row.append(self.playlist_mode)
        self.metadata_status = Gtk.Label(label="URL girip bilgi getirin", xalign=0)
        self.metadata_status.set_hexpand(True)
        self.metadata_status.add_css_class("video-meta")
        self.stop_scan_button = Gtk.Button(label="Taramayı Durdur")
        self.stop_scan_button.set_visible(False)
        self.stop_scan_button.connect("clicked", self._stop_scan)
        mode_row.append(self.metadata_status)
        mode_row.append(self.stop_scan_button)
        url_card.append(mode_row)
        page.append(url_card)

        self.download_content_stack = Gtk.Stack()
        self.download_content_stack.set_vexpand(True)
        self.download_content_stack.set_vhomogeneous(False)
        self.video_info_scroll = Gtk.ScrolledWindow()
        self.video_info_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.video_info_scroll.set_vexpand(True)
        self.video_info_scroll.set_propagate_natural_height(False)
        self.video_info_scroll.set_child(self._build_video_info_panel())
        self.download_content_stack.add_named(self.video_info_scroll, "video")

        playlist_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tools = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.playlist_search = Gtk.SearchEntry(placeholder_text="Playlist içinde ara…")
        self.playlist_search.set_hexpand(True)
        self.playlist_search.connect("search-changed", self._playlist_search_changed)
        tools.append(self.playlist_search)
        for label, mode, tooltip in (
            ("Filtredekileri Seç", "visible", "Arama sonucunda şu anda görünen videoları seçer"),
            ("Tümünü Seç", "all", "Playlistteki bütün videoları seçer"),
            ("Seçimi Kaldır", "none", "Playlistteki bütün seçimleri kaldırır"),
        ):
            button = Gtk.Button(label=label)
            button.set_tooltip_text(tooltip)
            button.connect("clicked", self._playlist_select, mode)
            tools.append(button)
        playlist_panel.append(tools)

        playlist_scroll = Gtk.ScrolledWindow()
        playlist_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        playlist_scroll.set_vexpand(True)
        self.playlist_view = Gtk.ListView.new(self.playlist_selection_model, self._playlist_factory())
        playlist_scroll.set_child(self.playlist_view)
        playlist_panel.append(playlist_scroll)
        self.download_content_stack.add_named(playlist_panel, "playlist")
        self.download_content_stack.set_visible_child_name("video")
        page.append(self.download_content_stack)

        format_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        format_card.add_css_class("card")
        format_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        format_row.append(self._label("Format", "section-title"))
        self.preset_dropdown = Gtk.DropDown.new_from_strings([preset.label for preset in PRESETS])
        default_index = next((index for index, preset in enumerate(PRESETS) if preset.id == self.config.get("default_preset")), 0)
        self.preset_dropdown.set_selected(default_index)
        self.preset_dropdown.set_hexpand(True)
        self.preset_dropdown.connect("notify::selected", self._preset_changed)
        format_row.append(self.preset_dropdown)
        format_card.append(format_row)
        self.custom_format_entry = Gtk.Entry(placeholder_text="Özel yt-dlp format ifadesi")
        self.custom_format_entry.set_text(str(self.config.get("custom_format", "")))
        self.custom_format_entry.set_visible(PRESETS[default_index].id == "custom")
        format_card.append(self.custom_format_entry)
        self.download_button = Gtk.Button(label="↓ İndir")
        self.download_button.add_css_class("suggested-action")
        self.download_button.add_css_class("big-button")
        self.download_button.set_sensitive(False)
        self.download_button.connect("clicked", self._download_selected)
        format_card.append(self.download_button)
        page.append(format_card)
        return page

    def _build_video_info_panel(self) -> Gtk.Widget:
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        panel.add_css_class("card")

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.video_thumbnail_stack = Gtk.Stack()
        self.video_thumbnail_stack.set_size_request(320, 180)
        self.video_thumbnail = Gtk.Picture()
        self.video_thumbnail.set_content_fit(Gtk.ContentFit.COVER)
        self.video_thumbnail.set_can_shrink(True)
        placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        placeholder.set_halign(Gtk.Align.CENTER)
        placeholder.set_valign(Gtk.Align.CENTER)
        placeholder.append(Gtk.Image.new_from_icon_name("video-x-generic-symbolic"))
        self.video_placeholder_label = Gtk.Label(label="Video URL'sini girip Bilgi Getir'e basın")
        self.video_placeholder_label.set_wrap(True)
        placeholder.append(self.video_placeholder_label)
        self.video_thumbnail_stack.add_named(placeholder, "placeholder")
        self.video_thumbnail_stack.add_named(self.video_thumbnail, "thumbnail")
        self.video_thumbnail_stack.set_visible_child_name("placeholder")
        content.append(self.video_thumbnail_stack)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        details.set_hexpand(True)
        self.video_title_label = Gtk.Label(label="Video bilgisi bekleniyor", xalign=0)
        self.video_title_label._i18n_label_skip = False
        self.video_title_label._i18n_tooltip_skip = False
        self.video_title_label.set_wrap(True)
        self.video_title_label.add_css_class("section-title")
        self.video_channel_label = Gtk.Label(label="", xalign=0)
        self.video_channel_label.add_css_class("video-meta")
        self.video_properties_label = Gtk.Label(label="", xalign=0)
        self.video_properties_label.set_wrap(True)
        self.video_source_label = Gtk.Label(label="", xalign=0)
        self.video_source_label.set_wrap(True)
        self.video_source_label.add_css_class("video-meta")
        details.append(self.video_title_label)
        details.append(self.video_channel_label)
        details.append(self.video_properties_label)
        details.append(self.video_source_label)
        content.append(details)
        panel.append(content)

        self.video_description_toggle = Gtk.ToggleButton()
        self.video_description_toggle.add_css_class("flat")
        self.video_description_toggle.add_css_class("description-toggle")
        self.video_description_toggle.set_sensitive(False)
        self.video_description_toggle.connect("toggled", self._toggle_video_description)
        description_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.video_description_title = Gtk.Label(label="Açıklamayı Göster", xalign=0, hexpand=True)
        self.video_description_icon = Gtk.Image.new_from_icon_name("pan-down-symbolic")
        description_header.append(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
        description_header.append(self.video_description_title)
        description_header.append(self.video_description_icon)
        self.video_description_toggle.set_child(description_header)
        panel.append(self.video_description_toggle)

        self.video_description_revealer = Gtk.Revealer()
        self.video_description_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.video_description_revealer.set_transition_duration(180)
        self.video_description_label = Gtk.Label(label="", xalign=0, yalign=0, selectable=True)
        self.video_description_label._i18n_label_skip = True
        self.video_description_label.set_wrap(True)
        self.video_description_label.add_css_class("video-meta")
        description_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        description_box.add_css_class("description-box")
        description_box.append(self.video_description_label)
        self.video_description_revealer.set_child(description_box)
        panel.append(self.video_description_revealer)
        return panel

    def _build_queue_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.add_css_class("page")
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.queue_count_label = Gtk.Label(label="Kuyruk boş", xalign=0)
        self.queue_count_label.set_hexpand(True)
        start_button = Gtk.Button(label="Bekleyenleri Başlat")
        start_button.connect("clicked", lambda *_: self.engine.start_available())
        clear_done = Gtk.Button(label="Tamamlananları Temizle")
        clear_done.connect("clicked", lambda *_: self.engine.clear_finished())
        clear_all = Gtk.Button(label="Tümünü Temizle")
        clear_all.add_css_class("destructive-action")
        clear_all.connect("clicked", self._confirm_clear_queue)
        toolbar.append(self.queue_count_label)
        toolbar.append(start_button)
        toolbar.append(clear_done)
        toolbar.append(clear_all)
        page.append(toolbar)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.queue_view = Gtk.ListView.new(self.queue_selection_model, self._queue_factory())
        scroll.set_child(self.queue_view)
        page.append(scroll)
        return page

    def _build_history_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.add_css_class("page")
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        history_group: Gtk.ToggleButton | None = None
        self.history_filter_buttons: dict[str, Gtk.ToggleButton] = {}
        for key, label in (("all", "Tümü"), ("audio", "Müzikler"), ("video", "Videolar")):
            button = Gtk.ToggleButton(label=label)
            if history_group:
                button.set_group(history_group)
            else:
                history_group = button
                button.set_active(True)
            button.connect("toggled", self._history_filter_changed, key)
            toolbar.append(button)
            self.history_filter_buttons[key] = button
        self.history_count_label = Gtk.Label(label="", xalign=0)
        self.history_count_label.set_hexpand(True)
        clear_button = Gtk.Button(label="Geçmişi Temizle")
        clear_button.add_css_class("destructive-action")
        clear_button.connect("clicked", self._confirm_clear_history)
        toolbar.append(self.history_count_label)
        toolbar.append(clear_button)
        page.append(toolbar)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.history_view = Gtk.ListView.new(self.history_selection_model, self._history_factory())
        scroll.set_child(self.history_view)
        page.append(scroll)
        return page

    @staticmethod
    def _history_kind(entry: HistoryEntry) -> str:
        return entry.kind

    def _history_filter_func(self, item: HistoryObject) -> bool:
        return self._history_filter_mode == "all" or self._history_kind(item.entry) == self._history_filter_mode

    def _history_filter_changed(self, button: Gtk.ToggleButton, mode: str) -> None:
        if not button.get_active():
            return
        self._history_filter_mode = mode
        self.history_filter.changed(Gtk.FilterChange.DIFFERENT)
        self._update_history_count()

    @staticmethod
    def _label(text: str, css_class: str = "") -> Gtk.Label:
        label = Gtk.Label(label=text, xalign=0)
        if css_class:
            label.add_css_class(css_class)
        return label

    def _switch_tab(self, button: Gtk.ToggleButton, key: str) -> None:
        if button.get_active():
            self.stack.set_visible_child_name(key)

    def _url_changed(self, entry: Gtk.Entry) -> None:
        playlist = is_playlist_url(entry.get_text())
        self.playlist_mode.set_active(playlist)
        self.video_mode.set_active(not playlist)

    def _download_mode_changed(self, button: Gtk.ToggleButton) -> None:
        if not button.get_active() or not hasattr(self, "download_content_stack"):
            return
        self._set_download_mode_view()

    def _set_download_mode_view(self) -> None:
        playlist = self.playlist_mode.get_active()
        self.download_content_stack.set_visible_child_name("playlist" if playlist else "video")
        self.stop_scan_button.set_visible(playlist and self._metadata_scanning)
        self._update_download_label()

    def _paste_url(self, *_args) -> None:
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.read_text_async(None, self._paste_finished)

    def _paste_finished(self, clipboard, result) -> None:
        try:
            text = clipboard.read_text_finish(result)
            if text:
                self.url_entry.set_text(text.strip())
        except GLib.Error as exc:
            LOGGER.warning("Pano okunamadı: %s", exc)

    def _check_clipboard(self) -> bool:
        if not self.config.get("clipboard", True) or self._closing:
            return not self._closing
        try:
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.read_text_async(None, self._clipboard_finished)
        except GLib.Error:
            LOGGER.debug("Pano isteği başarısız", exc_info=True)
        return True

    def _clipboard_finished(self, clipboard, result) -> None:
        try:
            text = (clipboard.read_text_finish(result) or "").strip()
            if text and text != self._clipboard_text and is_valid_url(text):
                self._clipboard_text = text
                self.toast_overlay.add_toast(Adw.Toast(title="Panoda desteklenen bir video bağlantısı bulundu"))
        except GLib.Error:
            LOGGER.debug("Pano sonucu okunamadı", exc_info=True)

    def _fetch_metadata(self) -> None:
        url = self.url_entry.get_text().strip()
        if not is_valid_url(url):
            self._show_error("Geçersiz URL", "Desteklenen bir video veya playlist bağlantısı girin.")
            return
        self.playlist_store.remove_all()
        self._video_info = None
        self._reset_video_info_panel("Bilgiler alınıyor…")
        self._playlist_title = "Oynatma Listesi"
        self._playlist_uploader = ""
        self._metadata_scanning = True
        self.download_button.set_sensitive(False)
        self.stop_scan_button.set_visible(self.playlist_mode.get_active())
        self.metadata_status.set_label("Bilgiler alınıyor…")
        self._metadata_token = self.scanner.start(url, self.playlist_mode.get_active())

    def _reset_video_info_panel(self, message: str = "Video URL'sini girip Bilgi Getir'e basın") -> None:
        self._thumbnail_token = ""
        self.video_thumbnail.set_paintable(None)
        self.video_thumbnail_stack.set_visible_child_name("placeholder")
        self.video_placeholder_label.set_label(message)
        self.video_title_label._i18n_label_skip = False
        self.video_title_label._i18n_tooltip_skip = False
        self.video_title_label.set_label("Video bilgisi bekleniyor")
        self.video_channel_label.set_label("")
        self.video_properties_label.set_label("")
        self.video_source_label.set_label("")
        self.video_description_label.set_label("")
        self.video_description_toggle.set_active(False)
        self.video_description_toggle.set_sensitive(False)
        self.video_info_scroll.get_vadjustment().set_value(0)

    def _render_video_info(self, info: dict[str, Any]) -> None:
        title = str(info.get("title") or "Bilinmeyen video")
        channel = str(info.get("uploader") or info.get("channel") or "Bilinmeyen kanal")
        duration = format_duration(info.get("duration", 0)) or "Bilinmiyor"
        views = self._format_count(info.get("view_count"))
        upload_date = self._format_upload_date(info.get("upload_date"))
        width = info.get("width")
        height = info.get("height")
        resolution = f"{width}×{height}" if width and height else str(info.get("resolution") or "Bilinmiyor")
        source = str(info.get("extractor_key") or info.get("extractor") or "Bilinmeyen kaynak")
        video_id = str(info.get("id") or "")

        self.video_title_label._i18n_label_skip = True
        self.video_title_label._i18n_tooltip_skip = True
        self.video_title_label.set_label(title)
        self.video_title_label.set_tooltip_text(title)
        self.video_channel_label.set_label(f"Kanal: {channel}")
        properties = [f"Süre: {duration}", f"İzlenme: {views}", f"Yayın: {upload_date}", f"Kaynak: {resolution}"]
        self.video_properties_label.set_label("   •   ".join(properties))
        self.video_source_label.set_label(f"Platform: {source}" + (f"   •   Video kimliği: {video_id}" if video_id else ""))
        description = str(info.get("description") or "")
        self.video_description_label._i18n_label_skip = bool(description)
        self.video_description_label.set_label(description or "Açıklama bulunmuyor.")
        self.video_description_toggle.set_active(False)
        self.video_description_toggle.set_sensitive(True)

        thumbnail = str(info.get("thumbnail") or "")
        if thumbnail:
            self.video_placeholder_label.set_label("Kapak resmi yükleniyor…")
            self._load_video_thumbnail(thumbnail)
        else:
            self.video_thumbnail_stack.set_visible_child_name("placeholder")
            self.video_placeholder_label.set_label("Kapak resmi bulunamadı")

    def _toggle_video_description(self, button: Gtk.ToggleButton) -> None:
        expanded = button.get_active()
        self.video_description_revealer.set_reveal_child(expanded)
        self.video_description_title.set_label("Açıklamayı Gizle" if expanded else "Açıklamayı Göster")
        self.video_description_icon.set_from_icon_name("pan-up-symbolic" if expanded else "pan-down-symbolic")

    @staticmethod
    def _format_count(value: Any) -> str:
        try:
            return f"{int(value):,}".replace(",", ".")
        except (TypeError, ValueError):
            return "Bilinmiyor"

    @staticmethod
    def _format_upload_date(value: Any) -> str:
        text = str(value or "")
        if len(text) == 8 and text.isdigit():
            return f"{text[6:8]}.{text[4:6]}.{text[:4]}"
        return text or "Bilinmiyor"

    def _load_video_thumbnail(self, url: str) -> None:
        token = str(uuid4())
        self._thumbnail_token = token

        def worker() -> None:
            try:
                request = urllib.request.Request(url, headers={"User-Agent": f"Downloader/{APP_VERSION}"})
                with urllib.request.urlopen(request, timeout=12) as response:
                    data = response.read(8_000_001)
                if len(data) > 8_000_000:
                    raise ValueError("Kapak resmi 8 MB sınırını aşıyor")
                GLib.idle_add(self._apply_video_thumbnail, token, data)
            except Exception as exc:
                LOGGER.warning("Kapak resmi alınamadı: %s", exc)
                GLib.idle_add(self._video_thumbnail_failed, token)

        threading.Thread(target=worker, daemon=True, name="video-thumbnail").start()

    def _apply_video_thumbnail(self, token: str, data: bytes) -> bool:
        if token != self._thumbnail_token or self._closing:
            return False
        try:
            texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))
            self.video_thumbnail.set_paintable(texture)
            self.video_thumbnail_stack.set_visible_child_name("thumbnail")
        except GLib.Error as exc:
            LOGGER.warning("Kapak resmi işlenemedi: %s", exc)
            self._video_thumbnail_failed(token)
        return False

    def _video_thumbnail_failed(self, token: str) -> bool:
        if token == self._thumbnail_token and not self._closing:
            self.video_thumbnail_stack.set_visible_child_name("placeholder")
            self.video_placeholder_label.set_label("Kapak resmi yüklenemedi")
        return False

    def _stop_scan(self, *_args) -> None:
        self.scanner.cancel()
        self._metadata_scanning = False
        self.stop_scan_button.set_visible(False)
        count = self.playlist_store.get_n_items()
        self.metadata_status.set_label(f"Tarama durduruldu · {count} video bulundu")
        self.download_button.set_sensitive(count > 0)

    def _playlist_filter_func(self, item: PlaylistObject) -> bool:
        return not self.playlist_query or self.playlist_query in item.search_text

    def _playlist_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self.playlist_query = entry.get_text().strip().casefold()
        self.playlist_filter.changed(Gtk.FilterChange.DIFFERENT)
        self._update_download_label()

    def _playlist_select(self, _button, mode: str) -> None:
        source = self.playlist_filtered if mode == "visible" else self.playlist_store
        selected = mode != "none"
        for index in range(source.get_n_items()):
            item = source.get_item(index)
            item.selected = selected
            item.notify("selected")
        self._update_download_label()

    def _preset_changed(self, *_args) -> None:
        preset = PRESETS[self.preset_dropdown.get_selected()]
        self.custom_format_entry.set_visible(preset.id == "custom")

    def _selected_playlist_entries(self) -> list[PlaylistEntry]:
        result: list[PlaylistEntry] = []
        for index in range(self.playlist_store.get_n_items()):
            item = self.playlist_store.get_item(index)
            if item.selected:
                result.append(item.entry)
        return result

    def _update_download_label(self) -> None:
        if self.video_mode.get_active():
            self.download_button.set_label("↓ Videoyu İndir")
            self.download_button.set_sensitive(bool(self._video_info) and not self._metadata_scanning)
            return
        count = len(self._selected_playlist_entries())
        self.download_button.set_label(f"↓ Seçilenleri İndir ({count})")
        self.download_button.set_sensitive(count > 0 and not self._metadata_scanning)

    def _download_selected(self, *_args) -> None:
        preset = PRESETS[self.preset_dropdown.get_selected()]
        custom = self.custom_format_entry.get_text().strip()
        if preset.id == "custom" and not custom:
            self._show_error("Format eksik", "Gelişmiş format alanına bir yt-dlp format ifadesi girin.")
            return
        self.config["default_preset"] = preset.id
        self.config["custom_format"] = custom
        self.storage.save_config(self.config)
        batch_id = str(uuid4())
        jobs: list[DownloadJob] = []
        if self.video_mode.get_active() and self._video_info:
            info = self._video_info
            jobs.append(
                DownloadJob(
                    url=str(info.get("webpage_url") or info.get("original_url") or self.url_entry.get_text()),
                    title=str(info.get("title") or "Bilinmeyen video"),
                    channel=str(info.get("uploader") or info.get("channel") or ""),
                    duration=float(info.get("duration") or 0),
                    thumbnail=str(info.get("thumbnail") or ""),
                    preset_id=preset.id,
                    custom_format=custom,
                    batch_id=batch_id,
                )
            )
        elif self.playlist_mode.get_active():
            for entry in self._selected_playlist_entries():
                jobs.append(
                    DownloadJob(
                        url=entry.url,
                        title=entry.title,
                        channel=entry.channel,
                        duration=entry.duration,
                        thumbnail=entry.thumbnail,
                        playlist_title=self._playlist_title,
                        playlist_index=entry.playlist_index,
                        preset_id=preset.id,
                        custom_format=custom,
                        batch_id=batch_id,
                    )
                )
        if not jobs:
            return
        known_urls = {
            item.url.strip().rstrip("/")
            for item in self.engine.snapshot()
            if item.status != DownloadStatus.CANCELLED.value
        }
        known_urls.update(entry.url.strip().rstrip("/") for entry in self.history)
        duplicates: list[DownloadJob] = []
        for job in jobs:
            normalized = job.url.strip().rstrip("/")
            if normalized in known_urls:
                duplicates.append(job)
            known_urls.add(normalized)
        if duplicates:
            self._show_duplicate_dialog(jobs, duplicates)
        else:
            self._add_jobs(jobs)

    def _show_duplicate_dialog(self, jobs: list[DownloadJob], duplicates: list[DownloadJob]) -> None:
        dialog = Adw.MessageDialog.new(
            self,
            "Tekrarlanan bağlantılar bulundu",
            f"{len(duplicates)} bağlantı kuyrukta veya geçmişte mevcut. Varsayılan olarak atlanacak.",
        )
        dialog.add_response("cancel", "Vazgeç")
        dialog.add_response("skip", "Tekrarları Atla")
        dialog.add_response("again", "Yeniden İndir")
        dialog.set_default_response("skip")
        dialog.set_response_appearance("again", Adw.ResponseAppearance.SUGGESTED)

        def response(_dialog, response_id: str) -> None:
            if response_id == "skip":
                duplicate_urls = {job.url.strip().rstrip("/") for job in duplicates}
                self._add_jobs([job for job in jobs if job.url.strip().rstrip("/") not in duplicate_urls])
            elif response_id == "again":
                for job in jobs:
                    if job in duplicates:
                        job.force_overwrite = True
                self._add_jobs(jobs)

        dialog.connect("response", response)
        dialog.present()

    def _add_jobs(self, jobs: list[DownloadJob]) -> None:
        if not jobs:
            self.toast_overlay.add_toast(Adw.Toast(title="Eklenecek yeni bağlantı yok"))
            return
        self.engine.add_jobs(jobs)
        self.tab_buttons["queue"].set_active(True)

    def _drain_events(self) -> bool:
        processed = 0
        while processed < 100:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)
            processed += 1
        return not self._closing or not self.events.empty()

    def _handle_event(self, event: DownloadEvent) -> None:
        if event.kind.startswith("metadata_"):
            self._handle_metadata_event(event)
            return
        if event.kind == "jobs_added":
            for job in event.payload["jobs"]:
                self.queue_store.append(JobObject(job))
        elif event.kind in ("job_updated", "job_progress"):
            obj = self._find_job_object(event.job_id)
            if obj:
                if event.kind == "job_progress":
                    job = obj.job
                    for key, value in event.payload.items():
                        setattr(job, key, value)
                    obj.sync(job)
                else:
                    job = event.payload["job"]
                    obj.sync(job)
                    if job.status == DownloadStatus.PENDING.value:
                        self._recorded_completions.discard(job.id)
                    if job.status == DownloadStatus.COMPLETED.value and job.id not in self._recorded_completions:
                        self._recorded_completions.add(job.id)
                        self._record_history(job)
                    if job.status == DownloadStatus.ERROR.value:
                        self._show_job_error(job)
            self.storage.save_queue(self.engine.snapshot())
        elif event.kind == "job_removed":
            self._remove_job_object(event.job_id)
        elif event.kind == "order_changed":
            self._populate_queue(event.payload["jobs"])
            self.storage.save_queue(event.payload["jobs"])
        elif event.kind == "queue_changed":
            self.storage.save_queue(self.engine.snapshot())
        elif event.kind == "batch_finished":
            self._batch_finished(event.payload)
        self._update_queue_count()

    def _handle_metadata_event(self, event: DownloadEvent) -> None:
        token = event.payload.get("token", "")
        if token and token != self._metadata_token:
            return
        if event.kind == "metadata_video":
            self._video_info = event.payload["info"]
            info = self._video_info
            self._render_video_info(info)
            duration = format_duration(info.get("duration", 0))
            self.metadata_status.set_label(
                f"{info.get('title', 'Bilinmeyen')} · {info.get('uploader', '')} · {duration}"
            )
        elif event.kind == "metadata_entries":
            self._playlist_title = event.payload.get("title") or self._playlist_title
            self._playlist_uploader = event.payload.get("uploader") or self._playlist_uploader
            for entry in event.payload["entries"]:
                self.playlist_store.append(PlaylistObject(entry))
            self.metadata_status.set_label(
                f"{self._playlist_title} · {self.playlist_store.get_n_items()} video bulundu…"
            )
        elif event.kind == "metadata_error":
            self._metadata_scanning = False
            self.stop_scan_button.set_visible(False)
            if self.video_mode.get_active():
                self.video_placeholder_label.set_label("Video bilgisi alınamadı")
            self._show_error("Bilgi alınamadı", str(event.payload.get("error", "Bilinmeyen hata")))
        elif event.kind == "metadata_finished":
            self._metadata_scanning = False
            self.stop_scan_button.set_visible(False)
            if self._video_info:
                self.download_button.set_sensitive(True)
            else:
                count = self.playlist_store.get_n_items()
                self.metadata_status.set_label(f"{self._playlist_title} · {count} video")
                self.download_button.set_sensitive(count > 0)
            self._update_download_label()

    def _record_history(self, job: DownloadJob) -> None:
        entry = HistoryEntry(
            title=job.title,
            url=job.url,
            output_path=job.output_path,
            preset_id=job.preset_id,
            channel=job.channel,
            duration=job.duration,
            completed_at=job.completed_at,
        )
        self.history.insert(0, entry)
        self.history = self.history[:500]
        self.history_store.insert(0, HistoryObject(entry))
        self.storage.save_history(self.history)
        self._update_history_count()

    def _batch_finished(self, payload: dict[str, Any]) -> None:
        completed = int(payload.get("completed", 0))
        failed = int(payload.get("failed", 0))
        text = f"{completed} indirme tamamlandı"
        if failed:
            text += f", {failed} hata"
        if self.config.get("notify", True):
            notification = Gio.Notification.new(tr("İndirme grubu tamamlandı"))
            notification.set_body(tr(text))
            self.get_application().send_notification(f"batch-{payload.get('batch_id')}", notification)
        self.toast_overlay.add_toast(Adw.Toast(title=text))
        folders = payload.get("folders") or []
        if self.config.get("open_folder", False) and folders:
            self._open_path(folders[0])

    def _populate_queue(self, jobs: list[DownloadJob]) -> None:
        self.queue_store.remove_all()
        for job in jobs:
            self.queue_store.append(JobObject(job))
        self._update_queue_count()

    def _find_job_object(self, job_id: str) -> JobObject | None:
        for index in range(self.queue_store.get_n_items()):
            obj = self.queue_store.get_item(index)
            if obj.job_id == job_id:
                return obj
        return None

    def _remove_job_object(self, job_id: str) -> None:
        for index in range(self.queue_store.get_n_items()):
            if self.queue_store.get_item(index).job_id == job_id:
                self.queue_store.remove(index)
                break

    def _update_queue_count(self) -> None:
        jobs = self.engine.snapshot()
        active = sum(job.status in (DownloadStatus.PENDING.value, DownloadStatus.DOWNLOADING.value, DownloadStatus.PAUSED.value) for job in jobs)
        self.queue_count_label.set_label("Kuyruk boş" if not jobs else f"{active} aktif / {len(jobs)} toplam")
        self.tab_buttons["queue"].set_label(f"Kuyruk ({active})" if active else "Kuyruk")

    def _populate_history(self) -> None:
        self.history_store.remove_all()
        for entry in self.history:
            self.history_store.append(HistoryObject(entry))
        self._update_history_count()

    def _update_history_count(self) -> None:
        visible = self.history_filtered.get_n_items()
        total = len(self.history)
        if not total:
            label = "Geçmiş boş"
        elif self._history_filter_mode == "all":
            label = f"{total} kayıt"
        else:
            label = f"{visible} gösteriliyor / {total} toplam"
        self.history_count_label.set_label(label)

    def _show_job_error(self, job: DownloadJob) -> None:
        self.toast_overlay.add_toast(Adw.Toast(title=f"İndirme hatası: {job.title[:60]}"))

    def _show_error(self, heading: str, details: str) -> None:
        LOGGER.error("%s: %s", heading, details)
        dialog = Adw.MessageDialog.new(self, heading, details[:600])
        dialog.add_response("close", "Kapat")
        dialog.add_response("copy", "Ayrıntıyı Kopyala")
        dialog.add_response("logs", "Log Klasörünü Aç")
        dialog.set_close_response("close")

        def response(_dialog, response_id: str) -> None:
            if response_id == "copy":
                Gdk.Display.get_default().get_clipboard().set(details)
            elif response_id == "logs":
                self._open_path(str(LOG_FILE.parent))

        dialog.connect("response", response)
        dialog.present()

    def _confirm_clear_queue(self, *_args) -> None:
        if not self.queue_store.get_n_items():
            return
        dialog = Adw.MessageDialog.new(self, "Kuyruk temizlensin mi?", "Aktif indirmeler iptal edilecek.")
        dialog.add_response("cancel", "Vazgeç")
        dialog.add_response("clear", "Tümünü Temizle")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda _d, response: self.engine.clear_all() if response == "clear" else None)
        dialog.present()

    def _confirm_clear_history(self, *_args) -> None:
        labels = {"all": "tüm", "audio": "müzik", "video": "video"}
        selected = labels[self._history_filter_mode]
        dialog = Adw.MessageDialog.new(
            self,
            "Geçmiş temizlensin mi?",
            f"{selected.capitalize()} geçmiş kayıtları silinir; indirilen dosyalar silinmez.",
        )
        dialog.add_response("cancel", "Vazgeç")
        dialog.add_response("clear", "Geçmişi Temizle")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)

        def response(_dialog, response_id: str) -> None:
            if response_id == "clear":
                if self._history_filter_mode == "all":
                    self.history.clear()
                else:
                    self.history[:] = [
                        entry
                        for entry in self.history
                        if self._history_kind(entry) != self._history_filter_mode
                    ]
                self._populate_history()
                self.storage.save_history(self.history)

        dialog.connect("response", response)
        dialog.present()

    def _play_path(
        self,
        path: str,
        retry: Callable[[], None] | None = None,
        title: str = "",
        items: list[MediaItem] | None = None,
    ) -> None:
        target = Path(path) if path else None
        if target and target.is_file():
            self._open_internal_player(target, title, items)
            return
        dialog = Adw.MessageDialog.new(
            self,
            "Dosya bulunamadı",
            "Dosya taşınmış veya silinmiş olabilir. Yeniden indirmek ister misiniz?",
        )
        dialog.add_response("cancel", "Vazgeç")
        if retry:
            dialog.add_response("retry", "Yeniden İndir")
            dialog.set_response_appearance("retry", Adw.ResponseAppearance.SUGGESTED)
            dialog.connect("response", lambda _d, response: retry() if response == "retry" else None)
        dialog.present()

    def _open_internal_player(
        self,
        target: Path,
        title: str = "",
        items: list[MediaItem] | None = None,
    ) -> None:
        for old_player in list(self._player_windows):
            old_player.close()

        media_items = items or [MediaItem(target, title or target.stem, self._media_kind(target))]
        start_index = next(
            (index for index, item in enumerate(media_items) if item.path == target),
            0,
        )
        player_window = MediaPlayerWindow(
            self,
            media_items,
            start_index=start_index,
            on_open_external=self._launch_external,
        )
        self._player_windows.append(player_window)

        def closed(*_args) -> bool:
            if player_window in self._player_windows:
                self._player_windows.remove(player_window)
            return False

        player_window.connect("close-request", closed)
        player_window.present()

    @staticmethod
    def _media_kind(target: Path) -> str:
        return "audio" if target.suffix.lower() in {".mp3", ".m4a", ".opus", ".ogg", ".wav", ".flac"} else "video"

    def _launch_external(self, target: Path) -> None:
        try:
            Gio.AppInfo.launch_default_for_uri(path_uri(target), None)
        except GLib.Error as exc:
            self._show_error("Dosya açılamadı", str(exc))

    def _open_path(self, path: str) -> None:
        target = Path(path).expanduser()
        folder = target if target.is_dir() else target.parent
        try:
            Gio.AppInfo.launch_default_for_uri(path_uri(folder), None)
        except GLib.Error as exc:
            self._show_error("Klasör açılamadı", str(exc))

    def _check_dependencies(self) -> bool:
        missing = [name for name in ("yt-dlp", "ffmpeg") if not shutil.which(name)]
        if missing:
            self._show_error("Eksik bağımlılık", f"Bulunamayan araçlar: {', '.join(missing)}\nKurulumu yeniden çalıştırın.")
        return False

    def _on_close_request(self, *_args) -> bool:
        if self._closing:
            return False
        if self.engine.has_active():
            dialog = Adw.MessageDialog.new(
                self,
                "İndirmeler devam ediyor",
                "İndirmeleri iptal edip uygulamadan çıkmak ister misiniz?",
            )
            dialog.add_response("stay", "Uygulamaya Dön")
            dialog.add_response("quit", "İndirmeleri İptal Et ve Çık")
            dialog.set_response_appearance("quit", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.connect("response", lambda _d, response: self._begin_shutdown() if response == "quit" else None)
            dialog.present()
            return True
        self._cleanup()
        return False

    def _begin_shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self.set_sensitive(False)

        def worker() -> None:
            self.scanner.cancel()
            self.engine.shutdown()
            self.storage.save_queue(self.engine.snapshot(), asynchronous=False)
            self.storage.save_history(self.history, asynchronous=False)
            self.storage.save_config(self.config, asynchronous=False)
            self.storage.close()
            GLib.idle_add(self.get_application().quit)

        threading.Thread(target=worker, daemon=True, name="shutdown").start()

    def _cleanup(self) -> None:
        if self._cleaned:
            return
        self._cleaned = True
        self.scanner.cancel()
        self.storage.save_queue(self.engine.snapshot(), asynchronous=False)
        self.storage.save_history(self.history, asynchronous=False)
        self.storage.save_config(self.config, asynchronous=False)
        self.storage.close()

    # Factory builders
    def _playlist_factory(self) -> Gtk.SignalListItemFactory:
        factory = Gtk.SignalListItemFactory()

        def setup(_factory, list_item: Gtk.ListItem) -> None:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.add_css_class("playlist-row")
            check = Gtk.CheckButton()
            index_label = Gtk.Label(width_chars=5, xalign=1)
            title = Gtk.Label(xalign=0, ellipsize=3)
            title.set_hexpand(True)
            duration = Gtk.Label(xalign=1)
            duration.add_css_class("video-meta")
            row.append(check)
            row.append(index_label)
            row.append(title)
            row.append(duration)
            widgets = {"check": check, "index": index_label, "title": title, "duration": duration, "object": None, "binding": False}
            check.connect("toggled", self._playlist_toggled, widgets)
            list_item._widgets = widgets
            list_item.set_child(row)

        def bind(_factory, list_item: Gtk.ListItem) -> None:
            obj: PlaylistObject = list_item.get_item()
            widgets = list_item._widgets
            widgets["object"] = obj
            widgets["binding"] = True
            widgets["check"].set_active(obj.selected)
            widgets["binding"] = False
            widgets["index"].set_label(f"{obj.entry.playlist_index}.")
            widgets["title"].set_label(obj.title)
            widgets["title"].set_tooltip_text(obj.title)
            widgets["duration"].set_label(format_duration(obj.entry.duration))
            widgets["handler"] = obj.connect("notify::selected", lambda *_: self._refresh_playlist_check(widgets))

        def unbind(_factory, list_item: Gtk.ListItem) -> None:
            widgets = list_item._widgets
            obj = widgets.get("object")
            if obj and widgets.get("handler"):
                obj.disconnect(widgets["handler"])
            widgets["object"] = None

        factory.connect("setup", setup)
        factory.connect("bind", bind)
        factory.connect("unbind", unbind)
        return factory

    def _playlist_toggled(self, check: Gtk.CheckButton, widgets: dict[str, Any]) -> None:
        obj = widgets.get("object")
        if obj and not widgets["binding"]:
            obj.selected = check.get_active()
            self._update_download_label()

    @staticmethod
    def _refresh_playlist_check(widgets: dict[str, Any]) -> None:
        obj = widgets.get("object")
        if obj:
            widgets["binding"] = True
            widgets["check"].set_active(obj.selected)
            widgets["binding"] = False

    def _queue_factory(self) -> Gtk.SignalListItemFactory:
        factory = Gtk.SignalListItemFactory()

        def setup(_factory, list_item: Gtk.ListItem) -> None:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            row.add_css_class("queue-row")
            info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            info.set_hexpand(True)
            title = BoundMarquee()
            meta = Gtk.Label(xalign=0, ellipsize=3)
            meta.add_css_class("video-meta")
            progress = Gtk.ProgressBar()
            info.append(title)
            info.append(meta)
            info.append(progress)
            status = Gtk.Label()
            status.add_css_class("status-badge")
            buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
            widgets: dict[str, Any] = {
                "title": title, "meta": meta, "progress": progress, "status": status,
                "buttons": {}, "object": None, "handlers": [],
            }
            for key, icon, tooltip, callback in (
                ("up", "go-up-symbolic", "Yukarı taşı", lambda job: self.engine.move(job.id, -1)),
                ("down", "go-down-symbolic", "Aşağı taşı", lambda job: self.engine.move(job.id, 1)),
                ("pause", "media-playback-pause-symbolic", "Duraklat / Devam", lambda job: self.engine.pause(job.id)),
                ("cancel", "process-stop-symbolic", "İptal", lambda job: self.engine.cancel(job.id)),
                ("retry", "view-refresh-symbolic", "Tekrar indir", lambda job: self.engine.retry(job.id)),
                ("details", "dialog-information-symbolic", "Hata ayrıntısı", lambda job: self._show_error("İndirme hatası", job.error)),
                ("play", "media-playback-start-symbolic", "Dosyayı oynat", lambda job: self._play_path(job.output_path, lambda: self.engine.retry(job.id, True), job.title)),
                ("folder", "folder-open-symbolic", "Klasörü aç", lambda job: self._open_path(job.output_path)),
                ("remove", "user-trash-symbolic", "Kaldır", lambda job: self.engine.remove(job.id)),
            ):
                button = Gtk.Button(icon_name=icon, tooltip_text=tooltip)
                button.connect("clicked", self._queue_action, widgets, callback)
                buttons.append(button)
                widgets["buttons"][key] = button
            drag = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
            drag.connect("prepare", self._drag_prepare, widgets)
            row.add_controller(drag)
            drop = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
            drop.connect("drop", self._drop_job, widgets)
            row.add_controller(drop)
            row.append(info)
            row.append(status)
            row.append(buttons)
            list_item._widgets = widgets
            list_item.set_child(row)

        def bind(_factory, list_item: Gtk.ListItem) -> None:
            obj: JobObject = list_item.get_item()
            widgets = list_item._widgets
            widgets["object"] = obj
            self._render_job(widgets, obj)
            widgets["handlers"] = [
                obj.connect(f"notify::{name}", lambda *_args, w=widgets, o=obj: self._render_job(w, o))
                for name in ("title", "status", "progress", "meta", "pending")
            ]

        def unbind(_factory, list_item: Gtk.ListItem) -> None:
            widgets = list_item._widgets
            obj = widgets.get("object")
            if obj:
                for handler in widgets.get("handlers", []):
                    obj.disconnect(handler)
            widgets["handlers"] = []
            widgets["object"] = None
            widgets["title"].unbind()

        factory.connect("setup", setup)
        factory.connect("bind", bind)
        factory.connect("unbind", unbind)
        return factory

    def _render_job(self, widgets: dict[str, Any], obj: JobObject) -> None:
        job = obj.job
        widgets["title"].bind(job.title)
        widgets["meta"].set_label(obj.meta)
        widgets["progress"].set_fraction(max(0, min(100, job.progress)) / 100)
        widgets["status"].set_label(STATUS_LABELS.get(job.status, job.status))
        for css in DownloadStatus:
            widgets["status"].remove_css_class(css.value)
        widgets["status"].add_css_class(job.status)
        pending = job.status == DownloadStatus.PENDING.value
        active = job.status in (DownloadStatus.DOWNLOADING.value, DownloadStatus.PAUSED.value)
        widgets["buttons"]["up"].set_visible(pending)
        widgets["buttons"]["down"].set_visible(pending)
        widgets["buttons"]["pause"].set_visible(active)
        widgets["buttons"]["pause"].set_icon_name(
            "media-playback-start-symbolic" if job.status == DownloadStatus.PAUSED.value else "media-playback-pause-symbolic"
        )
        widgets["buttons"]["cancel"].set_visible(job.status in (DownloadStatus.PENDING.value, DownloadStatus.DOWNLOADING.value, DownloadStatus.PAUSED.value))
        widgets["buttons"]["retry"].set_visible(job.status in (DownloadStatus.ERROR.value, DownloadStatus.CANCELLED.value))
        widgets["buttons"]["details"].set_visible(job.status == DownloadStatus.ERROR.value)
        widgets["buttons"]["play"].set_visible(job.status == DownloadStatus.COMPLETED.value)
        widgets["buttons"]["folder"].set_visible(bool(job.output_path))

    def _queue_action(self, _button, widgets: dict[str, Any], callback: Callable[[DownloadJob], Any]) -> None:
        obj = widgets.get("object")
        if obj:
            try:
                callback(obj.job)
            except Exception as exc:
                self._show_error("İşlem başarısız", str(exc))

    def _drag_prepare(self, _source, _x, _y, widgets: dict[str, Any]):
        obj = widgets.get("object")
        if not obj or not obj.pending:
            return None
        return Gdk.ContentProvider.new_for_value(obj.job_id)

    def _drop_job(self, _target, value: str, _x, _y, widgets: dict[str, Any]) -> bool:
        target = widgets.get("object")
        return bool(target and self.engine.move_before(str(value), target.job_id))

    def _history_factory(self) -> Gtk.SignalListItemFactory:
        factory = Gtk.SignalListItemFactory()

        def setup(_factory, list_item: Gtk.ListItem) -> None:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.add_css_class("history-row")
            info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            info.set_hexpand(True)
            title = BoundMarquee()
            meta = Gtk.Label(xalign=0)
            meta.add_css_class("video-meta")
            info.append(title)
            info.append(meta)
            play = Gtk.Button(icon_name="media-playback-start-symbolic", tooltip_text="Dosyayı oynat")
            folder = Gtk.Button(icon_name="folder-open-symbolic", tooltip_text="Klasörü aç")
            retry = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Tekrar indir")
            widgets = {"title": title, "meta": meta, "play": play, "folder": folder, "retry": retry, "object": None}
            play.connect("clicked", self._history_play, widgets)
            folder.connect("clicked", self._history_folder, widgets)
            retry.connect("clicked", self._history_retry, widgets)
            row.append(info)
            row.append(play)
            row.append(folder)
            row.append(retry)
            list_item._widgets = widgets
            list_item.set_child(row)

        def bind(_factory, list_item: Gtk.ListItem) -> None:
            obj: HistoryObject = list_item.get_item()
            widgets = list_item._widgets
            widgets["object"] = obj
            widgets["title"].bind(obj.title)
            widgets["meta"].set_label(obj.meta)

        def unbind(_factory, list_item: Gtk.ListItem) -> None:
            list_item._widgets["title"].unbind()
            list_item._widgets["object"] = None

        factory.connect("setup", setup)
        factory.connect("bind", bind)
        factory.connect("unbind", unbind)
        return factory

    def _history_play(self, _button, widgets: dict[str, Any]) -> None:
        obj = widgets.get("object")
        if obj:
            entry = obj.entry
            items = [
                MediaItem(Path(item.output_path), item.title, item.kind)
                for item in self.history
                if item.kind == entry.kind and item.output_path and Path(item.output_path).is_file()
            ]
            self._play_path(
                entry.output_path,
                lambda: self._redownload_history(entry),
                entry.title,
                items,
            )

    def _history_folder(self, _button, widgets: dict[str, Any]) -> None:
        obj = widgets.get("object")
        if obj:
            self._open_path(obj.entry.output_path)

    def _history_retry(self, _button, widgets: dict[str, Any]) -> None:
        obj = widgets.get("object")
        if obj:
            self._redownload_history(obj.entry)

    def _redownload_history(self, entry: HistoryEntry) -> None:
        job = DownloadJob(
            url=entry.url,
            title=entry.title,
            channel=entry.channel,
            duration=entry.duration,
            preset_id=entry.preset_id,
            force_overwrite=True,
        )
        self.engine.add_jobs([job])
        self.tab_buttons["queue"].set_active(True)

    # Settings and menu actions
    def _action_settings(self, *_args) -> None:
        SettingsWindow(self, self.config, self._settings_saved).present()

    def _settings_saved(self, config: dict[str, Any]) -> None:
        self.config = config
        set_language(str(config.get("language", "tr")))
        preset_index = next(
            (index for index, preset in enumerate(PRESETS) if preset.id == config.get("default_preset")),
            0,
        )
        self.preset_dropdown.set_selected(preset_index)
        self.custom_format_entry.set_text(str(config.get("custom_format", "")))
        self.custom_format_entry.set_visible(PRESETS[preset_index].id == "custom")
        self.storage.save_config(config)
        self._translate_windows()
        self.toast_overlay.add_toast(Adw.Toast(title=tr("Ayarlar kaydedildi")))

    def _action_update_ytdlp(self, *_args) -> None:
        self.toast_overlay.add_toast(Adw.Toast(title="yt-dlp güncelleniyor…"))

        def worker() -> None:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                if result.returncode:
                    raise RuntimeError((result.stderr or result.stdout)[-800:])
                GLib.idle_add(self.toast_overlay.add_toast, Adw.Toast(title="yt-dlp güncellendi"))
            except Exception as exc:
                GLib.idle_add(self._show_error, "yt-dlp güncellenemedi", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _action_open_logs(self, *_args) -> None:
        self._open_path(str(LOG_FILE.parent))

    def _action_about(self, *_args) -> None:
        about = Adw.AboutWindow(transient_for=self, modal=True)
        about.set_application_name(APP_NAME)
        about.set_version(APP_VERSION)
        about.set_developer_name("ForIntX / Muhammet Burak Akkaş")
        about.set_application_icon(APP_ID)
        about.set_license_type(Gtk.License.MIT_X11)
        about.set_comments(tr("GTK4 / Libadwaita tabanlı yt-dlp video ve playlist indirici."))
        about.set_website(WEBSITE_URL)
        about.present()


class SettingsWindow(Adw.Window):
    def __init__(self, parent: MainWindow, config: dict[str, Any], callback: Callable[[dict[str, Any]], None]) -> None:
        super().__init__(transient_for=parent, modal=True, title="Ayarlar")
        self.set_default_size(620, 700)
        self.config = copy.deepcopy(config)
        self.callback = callback
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.add_css_class("page")
        scroll.set_child(box)
        self.set_content(scroll)

        languages = ("Türkçe", "English")
        current_language = "English" if config.get("language") == "en" else "Türkçe"
        self.language = self._dropdown(languages, current_language)
        self._add_row(box, "Uygulama dili", self.language)

        self.folder = Gtk.Entry(text=str(config.get("folder", "")), hexpand=True)
        browse = Gtk.Button(label="Gözat")
        browse.connect("clicked", self._browse_folder)
        folder_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        folder_box.append(self.folder)
        folder_box.append(browse)
        self._add_row(box, "İndirme klasörü", folder_box)

        self.parallel = self._dropdown(PARALLEL_OPTIONS, str(config.get("parallel", "3")))
        self.fragments = self._dropdown(FRAGMENT_OPTIONS, str(config.get("concurrent_fragments", 4)))
        self.speed = self._dropdown(SPEED_LIMITS, str(config.get("speed_limit", "Sınırsız")))
        self._add_row(box, "Eş zamanlı indirme", self.parallel)
        self._add_row(box, "Paralel parçalar", self.fragments)
        self._add_row(box, "Hız sınırı", self.speed)

        preset_ids = tuple(preset.id for preset in PRESETS)
        preset_labels = tuple(preset.label for preset in PRESETS)
        current_preset = str(config.get("default_preset", "video-best-mp4"))
        current_preset_index = preset_ids.index(current_preset) if current_preset in preset_ids else 0
        self.default_preset = Gtk.DropDown.new_from_strings(preset_labels)
        self.default_preset._preset_ids = preset_ids
        self.default_preset.set_selected(current_preset_index)
        self.custom_format = Gtk.Entry(
            text=str(config.get("custom_format", "")),
            placeholder_text="Örn. 137+140",
            hexpand=True,
        )
        self._add_row(box, "Varsayılan format", self.default_preset)
        self._add_row(box, "Özel yt-dlp formatı", self.custom_format)

        self.filename = Gtk.Entry(text=str(config.get("filename_template", "%(title)s.%(ext)s")), hexpand=True)
        self.playlist_filename = Gtk.Entry(text=str(config.get("playlist_filename_template", "%(playlist_index)03d - %(title)s.%(ext)s")), hexpand=True)
        self._add_row(box, "Dosya adı şablonu", self.filename)
        self._add_row(box, "Playlist dosya şablonu", self.playlist_filename)

        self.notify = Gtk.Switch(active=bool(config.get("notify", True)))
        self.open_folder = Gtk.Switch(active=bool(config.get("open_folder", False)))
        self.clipboard = Gtk.Switch(active=bool(config.get("clipboard", True)))
        self.thumbnail = Gtk.Switch(active=bool(config.get("download_thumbnail", True)))
        self.metadata = Gtk.Switch(active=bool(config.get("embed_metadata", True)))
        self.chapters = Gtk.Switch(active=bool(config.get("keep_chapters", True)))
        self.playlist_folder = Gtk.Switch(active=bool(config.get("playlist_folder", True)))
        for label, widget in (
            ("Bildirim göster", self.notify),
            ("Grup bitince klasörü aç", self.open_folder),
            ("Pano bağlantılarını algıla", self.clipboard),
            ("Küçük resmi indir", self.thumbnail),
            ("Metadata göm", self.metadata),
            ("Bölümleri göm", self.chapters),
            ("Playlist için klasör oluştur", self.playlist_folder),
        ):
            self._add_row(box, label, widget)

        self.subtitles = Gtk.Switch(active=bool(config.get("download_subs", False)))
        self.auto_subs = Gtk.Switch(active=bool(config.get("sub_auto", False)))
        self.embed_subs = Gtk.Switch(active=bool(config.get("embed_subs", False)))
        self.sub_lang = self._dropdown(SUB_LANGS, str(config.get("sub_lang", "Türkçe")))
        self._add_row(box, "Altyazı indir", self.subtitles)
        self._add_row(box, "Otomatik altyazı", self.auto_subs)
        self._add_row(box, "Altyazıyı videoya göm", self.embed_subs)
        self._add_row(box, "Altyazı dili", self.sub_lang)

        cookie_modes = ("Yok", "Tarayıcı", "cookies.txt")
        mode_values = {"none": "Yok", "browser": "Tarayıcı", "file": "cookies.txt"}
        self.cookie_mode = self._dropdown(cookie_modes, mode_values.get(str(config.get("cookie_mode")), "Yok"))
        self.cookie_browser = self._dropdown(COOKIE_BROWSERS, str(config.get("cookie_browser", "firefox")))
        self.cookie_profile = Gtk.Entry(text=str(config.get("cookie_profile", "")), placeholder_text="İsteğe bağlı profil")
        self.cookie_file = Gtk.Entry(text=str(config.get("cookie_file", "")), hexpand=True)
        cookie_browse = Gtk.Button(label="Seç")
        cookie_browse.connect("clicked", self._browse_cookie)
        cookie_file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cookie_file_box.append(self.cookie_file)
        cookie_file_box.append(cookie_browse)
        self._add_row(box, "Çerez yöntemi", self.cookie_mode)
        self._add_row(box, "Tarayıcı", self.cookie_browser)
        self._add_row(box, "Tarayıcı profili", self.cookie_profile)
        self._add_row(box, "cookies.txt", cookie_file_box)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        reset = Gtk.Button(label="Varsayılanlara Dön")
        reset.connect("clicked", self._reset)
        save = Gtk.Button(label="Kaydet", hexpand=True)
        save.add_css_class("suggested-action")
        save.connect("clicked", self._save)
        actions.append(reset)
        actions.append(save)
        box.append(actions)

    @staticmethod
    def _add_row(parent: Gtk.Box, label: str, widget: Gtk.Widget) -> None:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        text = Gtk.Label(label=label, xalign=0, hexpand=True)
        row.append(text)
        row.append(widget)
        parent.append(row)

    @staticmethod
    def _dropdown(values, current: str) -> Gtk.DropDown:
        values = tuple(str(item) for item in values)
        dropdown = Gtk.DropDown.new_from_strings(values)
        dropdown._values = values
        dropdown.set_selected(values.index(current) if current in values else 0)
        return dropdown

    @staticmethod
    def _dropdown_value(dropdown: Gtk.DropDown) -> str:
        return dropdown._values[dropdown.get_selected()]

    def _browse_folder(self, *_args) -> None:
        dialog = Gtk.FileDialog(title=tr("İndirme klasörü seç"))
        dialog.select_folder(self, None, self._folder_selected)

    def _folder_selected(self, dialog, result) -> None:
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.folder.set_text(folder.get_path())
        except GLib.Error:
            pass

    def _browse_cookie(self, *_args) -> None:
        dialog = Gtk.FileDialog(title=tr("cookies.txt seç"))
        dialog.open(self, None, self._cookie_selected)

    def _cookie_selected(self, dialog, result) -> None:
        try:
            file = dialog.open_finish(result)
            if file:
                self.cookie_file.set_text(file.get_path())
        except GLib.Error:
            pass

    def _reset(self, *_args) -> None:
        self.close()
        SettingsWindow(self.get_transient_for(), dict(DEFAULT_CONFIG), self.callback).present()

    def _save(self, *_args) -> None:
        folder_text = self.folder.get_text().strip()
        if not folder_text or not self.filename.get_text().strip() or not self.playlist_filename.get_text().strip():
            self.get_transient_for()._show_error("Eksik ayar", "Klasör ve dosya adı şablonları boş bırakılamaz.")
            return
        folder = Path(folder_text).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            if not os.access(folder, os.W_OK):
                raise PermissionError("Klasöre yazma izni yok")
        except OSError as exc:
            self.get_transient_for()._show_error("Klasör kullanılamıyor", str(exc))
            return
        mode_label = self._dropdown_value(self.cookie_mode)
        mode = {"Yok": "none", "Tarayıcı": "browser", "cookies.txt": "file"}[mode_label]
        cookie_path = self.cookie_file.get_text().strip()
        if mode == "file" and not Path(cookie_path).expanduser().is_file():
            self.get_transient_for()._show_error("Çerez dosyası bulunamadı", cookie_path or "cookies.txt seçilmedi")
            return
        self.config.update(
            {
                "language": "en" if self._dropdown_value(self.language) == "English" else "tr",
                "folder": str(folder),
                "parallel": self._dropdown_value(self.parallel),
                "concurrent_fragments": int(self._dropdown_value(self.fragments)),
                "speed_limit": self._dropdown_value(self.speed),
                "default_preset": self.default_preset._preset_ids[self.default_preset.get_selected()],
                "custom_format": self.custom_format.get_text().strip(),
                "filename_template": self.filename.get_text(),
                "playlist_filename_template": self.playlist_filename.get_text(),
                "notify": self.notify.get_active(),
                "open_folder": self.open_folder.get_active(),
                "clipboard": self.clipboard.get_active(),
                "download_thumbnail": self.thumbnail.get_active(),
                "embed_metadata": self.metadata.get_active(),
                "keep_chapters": self.chapters.get_active(),
                "playlist_folder": self.playlist_folder.get_active(),
                "download_subs": self.subtitles.get_active(),
                "sub_auto": self.auto_subs.get_active(),
                "embed_subs": self.embed_subs.get_active(),
                "sub_lang": self._dropdown_value(self.sub_lang),
                "cookie_mode": mode,
                "cookie_browser": self._dropdown_value(self.cookie_browser),
                "cookie_profile": self.cookie_profile.get_text().strip(),
                "cookie_file": cookie_path,
            }
        )
        self.callback(self.config)
        self.close()


def run(argv: list[str] | None = None) -> int:
    application = VideoIndiriciApplication()
    return application.run(argv or sys.argv)
