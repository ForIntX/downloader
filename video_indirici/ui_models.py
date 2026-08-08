from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GObject, Gtk

from .models import DownloadJob, HistoryEntry, PlaylistEntry


class PlaylistObject(GObject.Object):
    def __init__(self, entry: PlaylistEntry):
        super().__init__()
        self.entry = entry

    @GObject.Property(type=str)
    def key(self) -> str:
        return self.entry.key

    @GObject.Property(type=str)
    def title(self) -> str:
        return self.entry.title

    @GObject.Property(type=str)
    def search_text(self) -> str:
        return f"{self.entry.title} {self.entry.channel}".casefold()

    @GObject.Property(type=bool, default=True)
    def selected(self) -> bool:
        return self.entry.selected

    @selected.setter
    def selected(self, value: bool) -> None:
        self.entry.selected = value


class JobObject(GObject.Object):
    def __init__(self, job: DownloadJob):
        super().__init__()
        self.job = job

    @GObject.Property(type=str)
    def job_id(self) -> str:
        return self.job.id

    @GObject.Property(type=str)
    def title(self) -> str:
        return self.job.title

    @GObject.Property(type=str)
    def status(self) -> str:
        return self.job.status

    @GObject.Property(type=float)
    def progress(self) -> float:
        return float(self.job.progress)

    @GObject.Property(type=str)
    def meta(self) -> str:
        parts = [part for part in (self.job.size, self.job.speed, self.job.eta) if part]
        if self.job.error:
            parts.append(self.job.error.splitlines()[-1][:120])
        if self.job.output_path:
            parts.append(self.job.output_path)
        return " • ".join(parts)

    @GObject.Property(type=bool, default=False)
    def pending(self) -> bool:
        return self.job.status == "pending"

    def sync(self, job: DownloadJob) -> None:
        self.job = job
        for name in ("title", "status", "progress", "meta", "pending"):
            self.notify(name)


class HistoryObject(GObject.Object):
    def __init__(self, entry: HistoryEntry):
        super().__init__()
        self.entry = entry

    @GObject.Property(type=str)
    def title(self) -> str:
        return self.entry.title

    @GObject.Property(type=str)
    def meta(self) -> str:
        return " • ".join(part for part in (self.entry.channel, self.entry.completed_at[:16].replace("T", " ")) if part)


class BoundMarquee(Gtk.ScrolledWindow):
    """A marquee whose frame callback exists only while a ListView row is bound."""

    def __init__(self) -> None:
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        self.set_propagate_natural_width(False)
        self.set_min_content_height(24)
        self.set_hexpand(True)
        self.label = Gtk.Label(xalign=0)
        self.label.set_single_line_mode(True)
        self.label.add_css_class("video-title")
        self.set_child(self.label)
        self._tick_id = 0
        self._direction = 1
        self._pause_until = 0
        self._text = ""

    def bind(self, text: str) -> None:
        if text == self._text and self._tick_id:
            return
        self._text = text
        self.label.set_label(text)
        self.set_tooltip_text(text)
        self.get_hadjustment().set_value(0)
        self._direction = 1
        self._pause_until = 0
        if not self._tick_id:
            self._tick_id = self.add_tick_callback(self._tick)

    def unbind(self) -> None:
        if self._tick_id:
            self.remove_tick_callback(self._tick_id)
            self._tick_id = 0
        self.label.set_label("")
        self._text = ""

    def _tick(self, _widget, frame_clock) -> bool:
        adjustment = self.get_hadjustment()
        limit = max(0.0, adjustment.get_upper() - adjustment.get_page_size())
        if limit <= 1:
            adjustment.set_value(0)
            return True
        now = frame_clock.get_frame_time()
        if now < self._pause_until:
            return True
        value = adjustment.get_value() + self._direction * 0.8
        if value >= limit:
            value = limit
            self._direction = -1
            self._pause_until = now + 1_200_000
        elif value <= 0:
            value = 0
            self._direction = 1
            self._pause_until = now + 1_200_000
        adjustment.set_value(value)
        return True
