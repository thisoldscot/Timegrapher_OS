# Timegrapher OS

[![CC BY-NC-SA 4.0][cc-by-nc-sa-shield]][cc-by-nc-sa]

## About the Project

| ![Timegrapher OS](https://github.com/fabemit/Timegrapher_OS/blob/main/images/Timegrapher_OS.png) |
| :-----------------------------------------------------------------------------------------------: |

Timegrapher OS is the desktop application for the Timegrapher Studio wristwatch
timegrapher. It measures **rate** (s/d), **beat error** (ms), **amplitude** (°)
and **beat rate** (BPH) from the escapement sound, timed against a DS3231 ±2 ppm
reference on an ESP32. Built around a pure-Python instrument core with a swappable
hardware-link registry, a CustomTkinter front-end, and a SQLite historian. See
[DESIGN.md](DESIGN.md) for the full design and the clock-discipline rationale.

---

## Features

- **Live diagnostics** — rate, beat error, amplitude, and BPH from escapement audio.
- **DS3231-disciplined timing** — ±2 ppm reference on an ESP32 for accurate rate.
- **Positional capture** — manual + timed auto-run with deltas, averages, pass/fail.
- **Movements database** — add/edit/delete, maker/caliber filters, CSV import/export.
- **Session historian** — save, browse with pass/fail preview, reopen trails.
- **Trends & scope** — rate/amplitude/beat-error graphs and a trigger-aligned
  beat-envelope oscilloscope.
- **PDF reports** — export the latest run or any saved record with a verdict.
- **Mock mode** — a synthetic movement drives the readouts with no hardware.

---

## Getting Started

### Requirements

- Python 3.10+
- Dependencies in `requirements.txt`: `customtkinter`, `pyserial`, `sqlalchemy`,
  `reportlab`, `pillow` (optional: `websockets` for Wi-Fi, `bleak` for BLE).

### Installation

```bash
git clone https://github.com/fabemit/Timegrapher_OS.git
cd Timegrapher_OS
pip install -r requirements.txt
```

### Usage

```bash
python main.py
```

With no hardware, pick **Mock (Demo)** in the device bar and Connect — a synthetic
movement drives the readouts and paper-tape trace. With hardware, pick
**Serial (USB)** and the ESP32's COM port. Run the tests with `python -m pytest`.

---

## Repository Contents

This repository is organised as follows:

- **`core/`** — pure-Python instrument engine (no Tk); shared with the mobile app.
- **`links/`** — transport registry (Serial / Wi-Fi / BLE / Mock) behind one `BaseLink`.
- **`ui/`** — CustomTkinter desktop front-end.
- **`tests/`** — ground-truth math + protocol round-trip tests.
- **`DESIGN.md`** — architecture and clock-discipline rationale.

Refer to the `CHANGELOG.md` for details about updates between versions.

---

## Timegrapher project

Timegrapher Studio is split across several repositories:

| Repository | Contents |
| --- | --- |
| [Timegrapher_OS](https://github.com/fabemit/Timegrapher_OS) | Desktop application (this repo) |
| [Timegrapher_App](https://github.com/fabemit/Timegrapher_App) | Mobile companion app |
| [Timegrapher_Firmware](https://github.com/fabemit/Timegrapher_Firmware) | ESP32 device firmware |
| [Timegrapher_Hat](https://github.com/fabemit/Timegrapher_Hat) | Carrier HAT (PCB) |
| [Timegrapher_PreAmp](https://github.com/fabemit/Timegrapher_PreAmp) | Piezo preamp (through-hole) |
| [Timegrapher_PreAmpSMD](https://github.com/fabemit/Timegrapher_PreAmpSMD) | Piezo preamp (SMD) |
| [Timegrapher_Stand](https://github.com/fabemit/Timegrapher_Stand) | 3D-printed stand & fixtures |

---

## Learn More

### Documentation

Setup and usage guides can be found here:
[ThisOldScot Docs](https://thisoldscot.com)
<!-- TODO: replace with the real docs URL when live -->

### ThisOldScot Community

ThisOldScot Community is a great space for the maker community — get answers to
your questions and solutions for our projects there.
<!-- TODO: add the real community/forum URL -->

### ThisOldScot Discord

Another option to get help and advice from other makers via the ThisOldScot Discord.
<!-- TODO: add the real Discord invite URL -->

---

## Contributing

Contributions are welcome! Here's how you can get involved:

- Submit pull requests to enhance the application or fix issues.
- Report bugs or problems by opening an issue.

We encourage community collaboration to make this project even better.

---

## About ThisOldScot

<img src="https://github.com/fabemit/Timegrapher_OS/blob/main/images/ThisOldScot_Logo.png" width="200" alt="ThisOldScot logo">

[ThisOldScot](https://thisoldscot.com) enjoys designing and making electronic
products and projects for enthusiasts, from hobbyists to professionals — boards,
sensors, hobby equipment, and anything else that catches my interest. Every
project is designed in-house and built on open-source hardware and software.

---

# Support the team
We :heart: doing research. New hardware (e.g. oscilloscopes, logic analysers,
servos, PCBs) is costly. Feel free to support us and accelerate our research.

Dev | ThisOldScot |
--- | --- |
Buy me a coffee | <a href="https://www.buymeacoffee.com/"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" height="20px"></a> |
Ko-fi | [![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/) |
<!-- TODO: add the real Buy Me a Coffee / Ko-fi URLs -->

---

## License

This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike
4.0 International License. Read more in the LICENSE file located in this repository.

Shield: [![CC BY-NC-SA 4.0][cc-by-nc-sa-shield]][cc-by-nc-sa]

[![CC BY-NC-SA 4.0][cc-by-nc-sa-image]][cc-by-nc-sa]

[cc-by-nc-sa]: http://creativecommons.org/licenses/by-nc-sa/4.0/
[cc-by-nc-sa-image]: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
[cc-by-nc-sa-shield]: https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg

---

**Disclaimer:**

This software is provided "AS IS", without warranty of any kind, either expressed
or implied. The entire quality and performance of what you do with the contents of
this repository is your responsibility. In no event will ThisOldScot be liable for
any damages or losses arising out of the use or inability to use the contents of
this repository.

> [!WARNING]
> Use responsibly and at your own risk.

---

## Have fun!

Thank you for your support from your fellow makers at ThisOldScot.

Happy Making!
