# Project Zancig

Project Zancig is an open-source framework for covert haptic signaling, intended for use in two-person mentalism and memory performance acts. It provides a standardized approach to encoding and transmitting information between a confederate and a performer using small, wearable consumer hardware.

The project is named after Julius and Agnes Zancig (1857–1929 and 1863–1916), Danish-American mentalists whose celebrated two-person telepathy act remains a foundational reference in the history of covert performance communication.

---

## What This Project Is

Zancig defines:

- A **haptic vocabulary** — a shared encoding standard for conveying numbers, signals, and structured data through vibration patterns
- An **input abstraction layer** — a set of named input schemes (Clock, Bump5, DirectMap, and others) that map physical button inputs on a given device to the values a routine requires
- A **routine format** — a specification for writing portable, platform-annotated performance routines in MicroPython, with declared capability requirements and input scheme preferences
- **Platform implementations** — device-specific firmware that implements the above on supported hardware

There is no single "Zancig core" codebase. The standard is the core. Implementations exist per hardware platform and are expected to diverge at the firmware level while remaining interoperable at the routine and vocabulary level.

---

## Supported Hardware

### Watchy (current)

The [Watchy](https://watchy.sqfmi.com/) by SQFMI is the first supported platform. It is an open-source e-paper smartwatch based on the ESP32, with four physical buttons and a haptic motor. Its watch form factor provides a natural, unobtrusive cover for performance use.

**Only Watchy V3 is officially supported.** Earlier hardware revisions differ in pin assignments and peripheral availability and have not been tested.

- MCU: ESP32
- Input: 4 physical buttons (configurable via input layout profiles)
- Haptic: ERM motor (vibration motor, driver-dependent)
- Runtime language: MicroPython
- Status: **Active**

Hardware pin assignments, register maps, and peripheral details used in the Zancig Watchy implementation were sourced from [Watchy_GSR](https://github.com/GuruSR/Watchy_GSR) by GuruSR, a comprehensive open-source Watchy firmware with extensive V3 hardware documentation. That project was instrumental in establishing accurate V3 specifications for the MicroPython port.

### Thumby Color (coming soon)

The [Thumby Color](https://thumby.us/) by TinyCircuits is a miniature handheld game device based on the RP2350. Work is underway to bring Zancig to this platform.

- MCU: RP2350
- Input: D-pad + A/B buttons
- Haptic: To be confirmed
- Runtime language: MicroPython
- Status: **Planned**

---

## Repository Structure

The repository is organized with each supported platform as a top-level directory. Routines live under their respective platform for now, as cross-platform compatibility is still being established. A `shared-routines/` directory will be added at the top level once portability patterns are better understood.

```
ZancigProject/
├── spec/                        # The Zancig Standard: haptic vocabulary, input schemes, routine format
├── docs/                        # Project documentation
├── Watchy/                      # Watchy V3 platform
│   ├── README.md                # Watchy-specific setup: flashing MicroPython, copying src/ to device
│   └── src/                     # Source files — mirrors the watch filesystem exactly
│       ├── main.py
│       ├── zancig.py
│       ├── epd_driver.py
│       └── routines/            # Routine source files
│           ├── calendar_prodigy.py
│           ├── knights_tour.py
│           └── ...
└── ThumbyColor/                 # Thumby Color platform (coming soon)
    ├── README.md
    └── src/                     # Source files — mirrors the device filesystem
        ├── main.py
        └── routines/
```

The `src/` directory under each platform mirrors the device filesystem directly. To deploy, flash MicroPython to the device and copy the contents of `src/` across. No structural translation is required between the repository and the device.

A `shared-routines/` directory will be introduced at the top level once sufficient experience has been gained to determine which routines can be reliably ported between platforms without modification.

---

## The Haptic Vocabulary

Zancig uses a configurable haptic encoding system rather than a single fixed vocabulary. Numbers are communicated as combinations of short and long pulses, where a configurable base number acts as the dividing line:

- Numbers below base: short pulses only (`*` = 1, `**` = 2, and so on)
- Base number: one long pulse (`-`)
- Numbers above base: long pulse followed by shorts (`-*` = base+1, `-**` = base+2, and so on)

All timing values — pulse duration, gap between pulses, and the feel of the jog input — are configurable per performer. The number range itself is also configurable; a routine that only needs values 1–6 can be tuned differently from one that needs 0–9.

**Default configuration:** base 5, range 1–9. This is a reasonable general-purpose starting point and what most documentation examples assume. A performer who trains on this default can work with any routine that uses standard range without reconfiguration.

The design intent is that a performer trains deeply on one encoding configuration rather than switching between fixed schemes. Configuring the system to match a specific routine's data range — and then training on that configuration — produces faster and more reliable recognition than a universal vocabulary would.

Timing and encoding parameters are set in the per-platform configuration file (e.g. `src/zancig_cfg.py` on Watchy). The full parameter reference is in [`spec/haptic-vocabulary.md`](spec/haptic-vocabulary.md).

---

## Input Schemes

Zancig separates *what a routine needs* from *how the performer inputs it*. Each routine declares a preferred input scheme. The performer selects a layout profile that maps their device's physical inputs to that scheme.

Input schemes vary by device capability and routine requirements. Examples include clock-face selection methods for numeric ranges and accelerometer-based tilt input where hardware supports it. All layouts support left- and right-hand configuration.

Input scheme definitions are in [`spec/input-schemes.md`](spec/input-schemes.md).

---

## Routines

Routines are the performance effects the system enables. Each routine is defined in a platform-neutral format that specifies:

- The effect and its performance context
- Required device capabilities (haptic, buttons, optional sensors)
- Preferred input scheme
- The encoding logic

Routines are located under the `src/routines/` directory of each platform. Contributions are welcome. See [Contributing](#contributing).

---

## Getting Started

### Watchy

See [`Watchy/README.md`](Watchy/README.md) for hardware requirements, flashing instructions, and configuration.

Prerequisites:

- Watchy V3 hardware
- Python 3.x with `esptool` installed
- MicroPython firmware for ESP32 (link in platform README)

---

## Contributing

Contributions are welcome, including new routines, platform ports, input scheme proposals, and corrections to the specification.

Before submitting a routine, review [`spec/routine-format.md`](spec/routine-format.md) to ensure it follows the standard declaration format, and place it under the appropriate platform directory. Routines that duplicate the core functionality of actively sold commercial products will not be accepted into the main routine library at this time.

Please open an issue before beginning significant new work, to avoid duplication of effort.

---

## Philosophy

Zancig is designed to be open and performer-modifiable. Routines are plain files. Encoding tables are readable. Nothing requires a proprietary update tool or a closed ecosystem.

The project does not attempt to be a commercial product. It is a technical framework for performers who want to understand and control their own tools.

The standard language is MicroPython wherever the target hardware supports it. Where it does not, the haptic vocabulary and routine format specification remain the reference, and platform authors are expected to document deviations clearly.

---

## License

Project Zancig uses a split license:

**Platform code, HAL, and routines** — licensed under the [GNU Lesser General Public License v3.0](LICENSE-CODE) (LGPL v3). You may use, modify, and distribute this code, including as part of a larger work, provided that modifications to the Zancig code itself are shared back under the same terms.

**Zancig Standard, specification documents, and documentation** (including this README) — licensed under [Creative Commons Attribution-ShareAlike 4.0 International](LICENSE-DOCS) (CC BY-SA 4.0). You may freely use, adapt, and redistribute these materials provided appropriate credit is given and derivatives are shared under the same license.

Routine files are LGPL v3 as code. The performance description and encoding logic documented in prose within a routine are CC BY-SA 4.0.

Contributions to the main repository are understood to be submitted under the applicable license for the component being contributed, as described above, unless explicitly stated otherwise.

On-device LGPL compliance for MicroPython platforms is satisfied by retaining the Zancig `.py` source files in editable form on the device, which is the default state of any MicroPython deployment.

---

## Attribution

Named after Julius and Agnes Zancig, whose work in the early twentieth century demonstrated the performative power of systematic covert communication. Their methods, their discipline, and their respect for the audience remain the spirit behind this project.
