"""TimegrapherApp — application shell.

Same skeleton as the sibling apps: a ctk.CTk window with a fixed icon sidebar
built from a registry, a connection bar, and a stack of view frames raised with
tkraise(). A background link thread feeds BeatEvents onto a queue that the Tk
main loop drains on a 50 ms tick — no cross-thread widget access.
"""
from __future__ import annotations

import queue

import customtkinter as ctk

from core.analyzer import MetricsAnalyzer
from core.historian import Historian
from core.movement_db import MovementDB
from core.session import Session
from core.settings_store import (
    SettingsStore, MOVEMENTS_USER_PATH, HISTORY_DB_PATH,
)
from links.link_manager import get_link

from ui.theme import (
    BG_MAIN, BG_CARD, BORDER_DARK, TXT_PRIMARY, TXT_SECONDARY, BRAND_CYAN,
    BTN_NAVY, FONT_TITLE, FONT_SMALL, RADIUS_LG, BORDER_W,
    apply_dark_titlebar, center_on_screen,
)
from ui.view_registry import ViewRegistry
from ui.connection_bar import ConnectionBar

# Importing the view modules registers them with ViewRegistry.
from ui.views import (  # noqa: F401
    live_view, trends_view, scope_view, positions_view,
    history_view, movements_view, settings_view, about_view,
)

UI_TICK_MS = 50


class TimegrapherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("Timegrapher Studio")
        center_on_screen(self, 1280, 800)
        self.after(100, lambda: apply_dark_titlebar(self))
        self.configure(fg_color=BG_MAIN)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # --- engine + state -------------------------------------------
        self.settings = SettingsStore()
        self.movement_db = MovementDB(MOVEMENTS_USER_PATH)
        self.analyzer = MetricsAnalyzer()
        self.apply_analyzer_settings()
        self.historian = Historian(HISTORY_DB_PATH)
        self.link = None
        self._beat_queue: queue.Queue = queue.Queue()
        self._wave_queue: queue.Queue = queue.Queue()

        # Per-session capture state.
        self.current_movement = None
        self.last_metrics = None
        self.session = Session(watch_name=self.settings.get("watch_name", ""))
        self._samples: list[dict] = []      # in-memory metric trail for Trends
        self._last_sample_t = 0.0

        # --- layout ---------------------------------------------------
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self._build_sidebar()
        self._build_main()
        self._build_views()

        self._restore_movement()
        self.select_view("live")
        self.after(UI_TICK_MS, self._tick)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_sidebar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0, width=132)
        bar.grid(row=0, column=0, sticky="nsw")
        bar.grid_propagate(False)

        ctk.CTkLabel(bar, text="TG", font=FONT_TITLE,
                     text_color=BRAND_CYAN).pack(pady=(18, 2))
        ctk.CTkLabel(bar, text="STUDIO", font=FONT_SMALL,
                     text_color=TXT_SECONDARY).pack(pady=(0, 16))

        self._nav_buttons: dict = {}
        for v in ViewRegistry.get_views():
            btn = ctk.CTkButton(
                bar, text=f"{v['icon']}\n{v['name']}", width=108, height=52,
                fg_color="transparent", hover_color=BG_MAIN,
                text_color=TXT_SECONDARY, font=("Helvetica", 11),
                command=lambda k=v["key"]: self.select_view(k))
            btn.pack(pady=3, padx=10)
            self._nav_buttons[v["key"]] = btn

    def _build_main(self) -> None:
        wrap = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        wrap.grid(row=0, column=1, sticky="nsew")
        wrap.grid_rowconfigure(1, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        self.connection_bar = ConnectionBar(wrap, self)
        self.connection_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        self.view_host = ctk.CTkFrame(wrap, fg_color=BG_MAIN, corner_radius=0)
        self.view_host.grid(row=1, column=0, sticky="nsew")
        self.view_host.grid_rowconfigure(0, weight=1)
        self.view_host.grid_columnconfigure(0, weight=1)

    def _build_views(self) -> None:
        self.views: dict = {}
        for v in ViewRegistry.get_views():
            frame = v["ui_class"](self.view_host, self)
            frame.grid(row=0, column=0, sticky="nsew")
            self.views[v["key"]] = frame

    def select_view(self, key: str) -> None:
        view = self.views.get(key)
        if not view:
            return
        view.tkraise()
        view.on_show()
        for k, btn in self._nav_buttons.items():
            active = (k == key)
            btn.configure(fg_color=BTN_NAVY if active else "transparent",
                          text_color=TXT_PRIMARY if active else TXT_SECONDARY)
        self._active_view = key
        # Only stream the (bandwidth-heavy) envelope while the scope is on screen.
        if self.link is not None:
            self.link.subscribe_waveform(key == "scope")

    # ------------------------------------------------------------------
    # Engine settings
    # ------------------------------------------------------------------
    def apply_analyzer_settings(self) -> None:
        self.analyzer.set_lift_angle(float(self.settings.get("lift_angle")))
        self.analyzer.set_bph_mode(self.settings.get("bph_mode"))
        self.analyzer.window_seconds = float(self.settings.get("window_seconds"))

    # ------------------------------------------------------------------
    # Movement selection — drives the header + this session's lift/bph
    # ------------------------------------------------------------------
    def _restore_movement(self) -> None:
        label = self.settings.get("selected_movement", "")
        m = self.movement_db.find(label) if label else None
        self.current_movement = m
        if m:
            self.session.movement_label = m.label
            self.session.bph = m.bph
            self.session.lift_angle = m.lift_angle
        self.connection_bar.set_movement(m.label if m else None)

    def select_movement(self, movement) -> None:
        """Adopt a movement for this session: pin lift angle + BPH from it."""
        self.current_movement = movement
        if movement is not None:
            self.settings.set("lift_angle", movement.lift_angle)
            self.settings.set("bph_mode", movement.bph)
            self.settings.set("selected_movement", movement.label)
            self.session.movement_label = movement.label
            self.session.bph = movement.bph
            self.session.lift_angle = movement.lift_angle
        else:
            self.settings.set("selected_movement", "")
            self.session.movement_label = ""
        self.settings.save()
        self.apply_analyzer_settings()
        self.connection_bar.set_movement(movement.label if movement else None)
        sv = self.views.get("settings")
        if sv is not None:
            sv.refresh_from_settings()

    def new_session(self) -> None:
        """Clear captured positions and the trend trail; keep movement/watch."""
        self.session = Session(
            watch_name=self.settings.get("watch_name", ""),
            movement_label=self.session.movement_label,
            bph=self.session.bph,
            lift_angle=self.session.lift_angle,
        )
        self._samples.clear()
        self._last_sample_t = 0.0
        for key in ("positions", "trends"):
            v = self.views.get(key)
            if v is not None:
                v.on_show()

    def samples(self) -> list[dict]:
        return self._samples

    # ------------------------------------------------------------------
    # Link connect / disconnect
    # ------------------------------------------------------------------
    def connect(self, kind: str, address: str) -> None:
        self.disconnect()
        try:
            link = get_link(kind, address)
            link.set_callbacks(on_beat=self._on_beat_threadsafe,
                               on_status=self._on_status_threadsafe,
                               on_waveform=self._on_wave_threadsafe)
            link.open()
        except Exception as exc:  # surface the failure on the bar
            self.connection_bar.set_connected(False, f"Error: {exc}")
            return
        self.link = link
        self.analyzer.reset()
        self.views["live"].reset()
        self._samples.clear()
        self._last_sample_t = 0.0
        self._last_status = None
        self._shown_status = None
        self.settings.set("link_kind", kind)
        self.settings.set("link_address", address)
        self.settings.save()
        self.connection_bar.set_connected(True, f"{kind} · {address or 'demo'}")
        # Resume the envelope stream if the user is already on the scope.
        link.subscribe_waveform(getattr(self, "_active_view", "live") == "scope")

    def disconnect(self) -> None:
        if self.link:
            self.link.close()
            self.link = None
        self.connection_bar.set_connected(False)

    def _on_beat_threadsafe(self, ev) -> None:
        # Called from the link reader thread — just enqueue the full event.
        self._beat_queue.put(ev)

    def _on_status_threadsafe(self, st) -> None:
        # Latest STATUS off the reader thread; reference assignment is atomic
        # under the GIL, so the UI tick can read it without a lock.
        self._last_status = st

    def _on_wave_threadsafe(self, wf) -> None:
        # Envelope chunk off the reader thread — drained on the UI tick.
        self._wave_queue.put(wf)

    # ------------------------------------------------------------------
    # UI tick — drain queue, update metrics + tape
    # ------------------------------------------------------------------
    def _tick(self) -> None:
        new_events = []
        try:
            while True:
                new_events.append(self._beat_queue.get_nowait())
        except queue.Empty:
            pass

        for ev in new_events:
            self.analyzer.add_beat(ev)

        metrics = self.analyzer.compute()
        self.last_metrics = metrics
        live = self.views["live"]
        bph = metrics.bph if metrics.valid else 28800
        for ev in new_events:
            live.push_beat(ev.onset_s, bph)

        if new_events and metrics.valid:
            self._log_sample(new_events[-1].onset_s, metrics)

        active_key = getattr(self, "_active_view", "live")
        active = self.views.get(active_key)

        # Drain envelope chunks (only the scope consumes them).
        new_waves = []
        try:
            while True:
                new_waves.append(self._wave_queue.get_nowait())
        except queue.Empty:
            pass
        if new_waves and active_key == "scope" and hasattr(active, "push_wave"):
            for wf in new_waves:
                active.push_wave(wf)

        if active:
            active.on_metrics(metrics)

        # Reflect the latest device STATUS on the connection bar when it changes.
        st = getattr(self, "_last_status", None)
        if st is not getattr(self, "_shown_status", None):
            self._shown_status = st
            self.connection_bar.set_device_status(st)

        self.after(UI_TICK_MS, self._tick)

    def _log_sample(self, t: float, m) -> None:
        """Append at most ~1 sample/sec to the in-memory trend trail."""
        if self._samples and (t - self._last_sample_t) < 1.0:
            return
        self._last_sample_t = t
        self._samples.append({
            "t": t, "rate": m.rate_s_per_day, "be": m.beat_error_ms,
            "amp": m.amplitude_deg, "bph": m.bph,
        })
        if len(self._samples) > 3600:        # cap ~1h of trail
            self._samples = self._samples[-3600:]

    def _on_close(self) -> None:
        self.disconnect()
        st = self.settings
        st.set("window_state", {"geometry": self.geometry()})
        st.save()
        self.destroy()
