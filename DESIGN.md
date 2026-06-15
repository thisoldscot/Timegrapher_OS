# Timegrapher Studio — Design Document

A fully-featured, accurate, easy-to-use **wristwatch timegrapher** for the desktop,
built to match the architecture and styling of *SI-Docs*, *PLC-SQL-Bridge*, and
*Sim Studio* (PLC_Simulator), and structured so the same core ports cleanly to a
mobile app.

Working name: **Timegrapher Studio** (System Integrator Apps family). Final name TBD.

---

## 1. Goals & non-goals

**Goals**
- Measure and display the four core watch metrics accurately and live:
  **rate** (s/d), **beat error** (ms), **amplitude** (°), and **beat rate / BPH**.
- The signature scrolling **"paper-tape" trace** plus rate / amplitude / beat-error
  trend graphs and a beat **oscilloscope** view.
- Multi-position workflow (DU/DD/CU/CD/PU/PL/PR) with delta analysis and reporting.
- Session recording, history, and PDF/CSV export — same persistence and export
  story as the other apps.
- Talk to the ESP32 over **USB serial** *and* **Wi-Fi**, behind one swappable
  link interface (so mobile, which can't do USB serial, uses Wi-Fi/BLE).
- Share a single pure-Python `core/` with no Tk dependency, so a mobile UI can sit
  on top of the same engine.

**Non-goals (v1)**
- No editing of the ESP32 firmware from the app (firmware is flashed separately).
- No cloud sync. History is local SQLite, same as the others.

---

## 2. Where the accuracy comes from (the hardware story)

The whole instrument lives or dies on its **time reference**. The ESP32's own
crystal is only ~±10–40 ppm and temperature-sensitive — at 40 ppm a watch would
read ~3.5 s/d off purely from the *instrument's* error, which is unacceptable for
a tool meant to resolve ±1 s/d.

Your hardware solves this: the **DS3231 is a TCXO accurate to ±2 ppm** (≈ ±0.17 s/d).
Its dedicated **32.768 kHz output** is wired to **GPIO34** (input-only — perfect, it
can't accidentally be driven). We use that 32 kHz square wave as the **disciplining
reference for the audio sample clock**, not the ESP32 crystal.

### Clock-discipline scheme
1. The **PCM1808** is clocked by the ESP32 **APLL → MCLK on GPIO0**, giving a
   nominally fixed sample rate (e.g. 48 kHz). But "nominal" drifts with the ESP32
   crystal.
2. The ESP32 **PCNT** (pulse-counter) peripheral counts DS3231 32 kHz edges on
   GPIO34 continuously.
3. Periodically (every audio block) we latch *(I2S samples elapsed, PCNT count)*.
   The **true** elapsed time of a block is `pcnt_delta / 32768.0` seconds — a
   ±2 ppm number — regardless of how the APLL actually ran.
4. Every beat's sample index therefore converts to a **TCXO-disciplined timestamp**.
   Rate is computed against *that* time base, so the instrument inherits the
   DS3231's ±2 ppm, not the ESP32's drift.

This is the single most important design decision: **all timing is expressed in
DS3231 ticks, the audio just supplies the events.**

### Signal chain
```
27 mm piezo disc → AD828 preamp (×gain, 5 V) → PCM1808 ADC (I2S, 24-bit)
        → ESP32 I2S RX → onset/beat detection → beat events (DS3231-timed)
DS3231 32 kHz → GPIO34 → PCNT → sample-clock discipline
ILI9341 SPI TFT ← ESP32 (standalone on-device readout)
ESP32 ⇄ Host (USB serial / Wi-Fi) — events + optional decimated waveform
```

### Pin map (as supplied — firmware constants)
| Subsystem | Signal | ESP32 GPIO |
|---|---|---|
| PCM1808 I2S | MCLK | 0 (APLL routed) |
| | BCLK | 26 |
| | LRCK | 25 |
| | DATA (DOUT) | 33 |
| DS3231 I2C | SDA | 21 |
| | SCL | 22 |
| | 32 kHz out | 34 (input-only, PCNT + ISR) |
| ILI9341 SPI (VSPI) | MOSI | 23 |
| | MISO | 19 |
| | SCK | 18 |
| | CS | 15 |
| | DC | 2 |
| | RESET | 4 |

---

## 3. Split of responsibility: ESP32 vs host

Two extremes are possible — stream raw audio to the host and do all DSP there
(heavy: 48 kHz × 24-bit ≈ 1.15 Mbit/s, awkward over Wi-Fi/BLE and on mobile), or
do everything on the ESP32 (no rich host visuals). We take the **hybrid** path:

**ESP32 does (timing-critical, must stay near the precise clock):**
- I2S capture, DC-block / band-pass filter, envelope follower.
- **Beat detection**: find each beat's onset and the secondary transients within it.
- Per beat emit a compact **BeatEvent**: DS3231-disciplined onset timestamp, the
  intra-beat transient offsets (for amplitude), and peak level.
- Drive the **ILI9341** with a standalone readout so the device is useful with no host.

**Host does (presentation + heavy/flexible analysis):**
- BPH auto-detection, rate / beat-error / amplitude math, position tracking.
- Paper-tape rendering, trend graphs, statistics, history, export.
- Optionally request a **decimated waveform stream** (e.g. 4–8 kHz envelope) purely
  for the oscilloscope view — small enough for Wi-Fi and mobile.

This keeps the link light enough for BLE/Wi-Fi/mobile while the ±2 ppm timing stays
on the hardware that owns the precise clock. Raw-audio streaming is an *optional*
diagnostic mode over USB only.

---

## 4. The math (so the readouts are correct)

Definitions: `bph` = beats per hour; beats per second `bps = bph/3600`.
Each beat is a half-oscillation, so the balance's **full oscillation period**
`T_osc = 7200 / bph` seconds. Beat timestamps `t₀, t₁, t₂…` are in DS3231 seconds.

**Beat rate / BPH** — detect from the median raw beat interval `Δ̄`:
`bph ≈ 3600 / Δ̄`, then snap to the nearest standard train
(18000, 19800, 21600, 25200, 28800, 36000) unless the user pins it manually.

**Rate (seconds/day)** — robust slope method (this *is* the paper-tape slope):
accumulate phase error `e_n = t_n − n·(3600/bph)` and least-squares fit
`e_n ≈ a + b·t_n`. Then
`rate_s_per_day = −b · 86400` (sign: positive = running fast).
The slope fit rejects single-beat jitter far better than differencing.

**Beat error (ms)** — the tick/tock asymmetry, the vertical gap between the two
tape lines:
`beat_error_ms = |interval(tick→tock) − interval(tock→tick)| × 1000`,
averaged over the window (i.e. mean of `|Δ_odd − Δ_even|`).

**Amplitude (degrees)** — from the time `Δt` between the two impulse noises inside
one beat. Modelling the balance as `θ(t) = A·sin(2π t / T_osc)` with the impulse
symmetric about the equilibrium crossing over the **lift angle** `L`:

```
A = (L / 2) / sin( π · Δt · bph / 7200 )
```

`L` (lift angle) is movement-specific (typically 52°, range ≈ 38–60°). It is a
user setting, pre-fillable from the **movement database** (caliber → lift angle, bph).
Amplitude accuracy depends entirely on reliably resolving the intra-beat `Δt`, which
is why the ESP32 reports per-beat transient offsets rather than just one onset.

All four are computed over a sliding window (default ~last 4–8 s, user-settable),
with outlier rejection (MAD filter) before the fits.

---

## 5. Software architecture

Mirrors the existing apps exactly: `ctk.CTk` shell, shared `theme.py`, a
`tk.PanedWindow` three-pane layout, **registry-driven views**, **registry-driven
hardware links**, SQLite historian via SQLAlchemy, and a pure-Python core.

```
Timegrapher/
  main.py                      # from ui.main_window import TimegrapherApp; app.mainloop()
  requirements.txt
  config.json                  # last device, gain, lift angle, window state…
  DESIGN.md                    # this file

  core/                        # PURE PYTHON — no tkinter import anywhere (mobile-shareable)
    __init__.py
    constants.py               # standard BPH set, default lift angle, window sizes
    beat_event.py              # BeatEvent / WaveformChunk dataclasses (wire types)
    analyzer.py                # MetricsAnalyzer: events → rate/beat-error/amplitude/bph
    bph_detector.py            # raw-interval → BPH snap
    movement_db.py             # caliber → (lift angle, bph) lookup; bundled JSON
    session.py                 # a measurement session: positions, samples, notes
    historian.py               # SQLite (SQLAlchemy) store of sessions & samples
    settings_store.py          # config.json load/save (like utils/config_manager)

  links/                       # HARDWARE LINK REGISTRY (mirrors hardware/plc_manager.py)
    __init__.py
    base_link.py               # BaseLink(ABC): open/close/read_event/stream_waveform
    protocol.py                # framing + encode/decode of BeatEvent/Waveform/Command
    serial_link.py             # SerialLink  (pyserial)  — desktop USB
    wifi_link.py               # WifiLink    (TCP socket / WebSocket) — desktop + mobile
    ble_link.py                # BleLink     (optional, mobile) — bleak
    link_manager.py            # get_link(kind, address) + registered_link_types()
    mock_link.py               # synthetic beat generator for UI dev & tests (no hardware)

  ui/                          # DESKTOP UI (CustomTkinter) — swapped out on mobile
    theme.py                   # copied verbatim from the other projects
    main_window.py             # TimegrapherApp: sidebar + view host + connection bar
    base_view.py               # BaseView(ctk.CTkFrame) — shared header/lifecycle
    view_registry.py           # ViewRegistry.register(...) (mirrors ModuleRegistry)
    connection_bar.py          # link kind + address + Connect/Disconnect + status
    views/
      live_view.py             # the main instrument: 4 big readouts + paper tape
      paper_tape.py            # the scrolling dot-trace canvas widget
      trends_view.py           # rate/amplitude/beat-error over time
      scope_view.py            # beat-waveform oscilloscope (decimated stream)
      positions_view.py        # multi-position grid + delta analysis
      history_view.py          # past sessions, reopen, compare
      movements_view.py        # movement database browser/editor
      settings_view.py         # gain, lift angle, BPH mode, window length, device
      about_view.py
    widgets/
      readout_tile.py          # big metric tile (value + units + trend arrow)
      gauge.py                 # amplitude arc gauge, beat-error bar

  export/                      # mirrors SI-Docs core/exporter*
    report.py                  # session → PDF (reportlab) and CSV

  firmware/                    # ESP32 source (PlatformIO / Arduino), flashed separately
    src/main.cpp, i2s_capture.*, beat_detect.*, ds3231_clock.*, display.*, link.*
    platformio.ini
    PROTOCOL.md                # the wire protocol spec (also summarised below)

  tests/
    test_analyzer.py           # known synthetic beats → expected rate/amp/BE
    test_bph_detector.py
    test_protocol.py           # round-trip encode/decode
    test_serial_link.py        # against mock serial
```

### Key pattern reuse
- **`view_registry.ViewRegistry`** — copy of SI-Docs `ModuleRegistry`
  (`key, name, icon, ui_class, order`). `main_window` builds the sidebar from the
  registry and `tkraise`s stacked view frames (the Sim Studio perf pattern), so
  switching views is instant.
- **`links/`** — copy of the `BasePLC` + `plc_manager` registry idea. `BaseLink`
  is the ABC; `link_manager.get_link("Serial (USB)", port)` returns a connected
  link; `registered_link_types()` feeds the connection-bar dropdown. `MockLink`
  lets the whole UI run with no hardware.
- **`theme.py`** — imported verbatim; every widget pulls colours/fonts/geometry
  from it, so the app is visually identical to the family (dark, `BG_MAIN`/`BG_CARD`,
  `BRAND_CYAN` accent, Consolas for numeric readouts).
- **`historian.py`** — same SQLAlchemy/SQLite approach as Sim Studio's historian,
  storing sessions and per-sample metrics for the trend graphs and history view.
- **`settings_store.py`** — same `config.json` round-trip as `utils/config_manager`,
  including persisted window state and last-used device.

### Threading model (same as the others)
A background **reader thread** owns the link, decodes frames into `BeatEvent`s, and
pushes them onto a `queue.Queue`. The Tk main loop drains the queue on a ~50 ms
`after()` tick, feeds `MetricsAnalyzer`, and updates readouts/canvas. No Tk calls
off-thread — identical to the PLC-SQL-Bridge engine thread + UI separation.

---

## 6. Mobile transferability

The split is deliberate so a mobile app reuses everything below the UI line:

| Layer | Desktop | Mobile |
|---|---|---|
| `core/` (analyzer, session, bph, movement db) | ✅ shared, pure Python | ✅ same code |
| `links/` | Serial + Wi-Fi + Mock | **Wi-Fi / BLE** (no USB serial) |
| `historian` | SQLite | SQLite (same file format) |
| UI | CustomTkinter (`ui/`) | **Flet** or **BeeWare/Toga** (new `ui_mobile/`) |
| Export | reportlab | reportlab / share sheet |

Recommended mobile UI toolkit: **Flet** — it's Python, renders a Flutter UI on
iOS/Android, keeps you in one language, and can also run the desktop build, so
`core/` + `links/wifi_link.py` are literally reused. The ESP32 runs a Wi-Fi server
(SoftAP or station), the phone connects to the same event/waveform protocol. BLE is
the fallback `BleLink` (via `bleak`) for a cable-free, no-network setup.

Because `core/` never imports Tk, the desktop and mobile front-ends are the only
thing that differs — the instrument logic is written once.

---

## 7. Host ⇄ ESP32 wire protocol (summary)

Length-prefixed frames, transport-agnostic (same bytes over serial, TCP, BLE).
`[0xA5][type:u8][len:u16][payload][crc16]`. Numeric/JSON hybrid: control is small
JSON, hot-path beat events are packed binary.

| Type | Dir | Payload |
|---|---|---|
| `HELLO` | ESP→host | firmware ver, sample rate, features |
| `BEAT` | ESP→host | `seq:u32`, `onset_ticks:u64` (DS3231 32 kHz ticks), `dt_ticks:u16` (intra-beat Δt), `level:u16` |
| `WAVE` | ESP→host | decimated envelope block (only if subscribed) |
| `STATUS` | ESP→host | gain, pcnt health, temperature (DS3231), clock-lock flag |
| `CMD` | host→ESP | JSON: set gain, set decimation, subscribe/unsubscribe waveform, ping |

`onset_ticks` in DS3231 32 kHz units is the canonical timestamp — the host divides
by 32768 for seconds. `dt_ticks` feeds the amplitude formula directly. Full spec
lives in `firmware/PROTOCOL.md`.

---

## 8. Build & deps (matches the family's PyInstaller story)

`requirements.txt`: `customtkinter`, `pyserial`, `numpy`, `sqlalchemy`,
`reportlab`, `pillow`, `bleak` (optional, mobile/BLE), `websockets` (Wi-Fi option).
NumPy is the only new heavyweight and is justified by the slope/MAD fits; the
analyzer is written to also work without it (pure-Python fallback) to keep the
mobile/Flet bundle lean.

Packaged with PyInstaller exactly like SI-Docs / PLC-SQL-Bridge (`.spec`, dark
title-bar via `apply_dark_titlebar`, app icon). Firmware is a separate PlatformIO
project under `firmware/` flashed with `pio run -t upload`.

---

## 9. Suggested build order

1. **`core/` + `links/mock_link.py` + tests** — prove the math against synthetic
   beats with no hardware. (`test_analyzer` with a generated 28800 bph, known
   amplitude/beat-error stream.)
2. **`ui/` shell** (theme, main_window, registry, connection bar) running on
   `MockLink` — get the paper tape and four readouts live.
3. **ESP32 firmware**: I2S + DS3231 PCNT discipline + beat detect + serial link;
   validate timestamps against a reference.
4. **`SerialLink`** end-to-end on a real movement; calibrate gain/threshold.
5. **`WifiLink`** + standalone ILI9341 readout.
6. **Positions, history, trends, export.**
7. **Mobile (Flet) front-end** reusing `core/` + `WifiLink`/`BleLink`.

---

## 10. Open decisions (your call before scaffolding)

- **App name** — "Timegrapher Studio" to sit beside *Sim Studio*, or something else?
- **Primary transport for v1** — start on **USB serial** (simplest, most reliable
  for bring-up) then add Wi-Fi, or go Wi-Fi-first to share the link with mobile
  from day one? (Recommendation: serial first, it de-risks the timing work.)
- **Mobile toolkit** — Flet (recommended) vs BeeWare/Toga.
- **Raw-audio streaming mode** — include the USB-only diagnostic raw stream in v1,
  or defer it (envelope/decimated waveform is enough for the scope view)?
