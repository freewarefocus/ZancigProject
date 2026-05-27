# Watchy Sleep States

The Watchy uses a three-state power model to maximize battery life on a 200mAh LiPo. Without sleep management, the 80MHz polling loop drains the battery in 4-6 hours. With it, standby life extends to weeks.

## State Diagram

```
               button press
  ACTIVE  ----30s idle---->  DARK  ----10s idle---->  DEEP SLEEP
    ^                         |                           |
    |      button press       |                           |
    +<------------------------+                           |
    |                                                     |
    +<-------------- button press (full reboot) ----------+
```

## States

### Active

Normal operating mode. The menu is displayed and buttons are polled every 5 seconds.

| Property | Value |
|----------|-------|
| CPU | 80MHz |
| Display | On (last-drawn frame) |
| Accelerometer | On (100Hz) |
| Motor | Idle |
| Current draw | ~35mA |
| Battery life | ~6 hours |
| Entry | Boot, button press from Dark |
| Exit | 30s idle -> Dark, long-press BL -> Python mode, long-press TR -> routine |

Battery is checked every 5 minutes. If battery is at or below 5%, a low battery warning is shown and the device enters Deep Sleep.

### Dark

Screen is blanked to save e-paper ghosting and appear fully off. The CPU remains active at 80MHz, polling buttons every 2 seconds. This is a brief transitional state -- it exists so a quick button press can restore the menu without a full reboot.

| Property | Value |
|----------|-------|
| CPU | 80MHz |
| Display | Blanked (partial refresh, no flash) |
| Accelerometer | On |
| Motor | Idle |
| Current draw | ~34mA |
| Battery life | ~6 hours |
| Entry | 30s idle from Active |
| Exit | Button press -> Active (menu redrawn), 10s idle -> Deep Sleep |

A button press during Dark mode redraws the menu and resets the idle timer. The press itself is consumed (not forwarded as a menu action).

### Deep Sleep

ESP32-S3 hardware deep sleep. All peripherals are suspended, the screen retains a blank image (e-paper needs zero power to hold), and current draw drops to micro-amps. Waking from deep sleep is a full reboot -- `main.py` runs from scratch.

| Property | Value |
|----------|-------|
| CPU | Deep sleep |
| Display | EPD sleep mode (retains blank image, zero power) |
| Accelerometer | Suspended (~3.5uA) |
| Motor | Off |
| Current draw | ~10-20uA |
| Battery life | ~1-2 years |
| Entry | 40s total idle (30s Active + 10s Dark), or low battery |
| Exit | Any of 4 buttons pressed (full reboot, ~2s) |

## Wake Mechanism

Deep sleep wake uses `esp32.wake_on_ext1()` with all four button GPIOs (0, 7, 6, 8) in `WAKEUP_ALL_LOW` mode. Since the buttons are active-low with pull-ups, pressing any button pulls the line low and triggers the wake interrupt.

Wake from deep sleep is a full reboot: hardware re-initializes, `main.py` runs, and the menu appears. This takes about 2 seconds including the first full e-paper refresh.

## Sleep Preparation Sequence

Before entering deep sleep, `zancig.prepare_sleep()` runs the following shutdown sequence:

1. Motor off
2. BMA423 accelerometer suspended (advanced power save mode)
3. Framebuffer cleared
4. Partial display refresh (blanks screen in ~0.3s, no flash)
5. EPD enters deep sleep (holds blank image at zero power)

This ensures the screen shows nothing when the battery eventually dies, rather than a stale "100%" frame.

## USB Connected

When USB is connected (detected via GPIO 21), sleep timers are disabled entirely. The device stays in Active mode, keeping the menu displayed and the REPL accessible for updating routines and Zancig software via Thonny. The Watchy charges while connected, so there is no battery drain concern.

This eliminates the main need for Python mode during normal use -- you can just plug in and transfer files without the device going dark or sleeping mid-transfer.

## Python Mode

Long-pressing BL (bottom-left) from the Active menu enters Python mode. This is a development/debug escape hatch -- the CPU clocks up to 240MHz and the device drops to the MicroPython REPL for use with Thonny or a serial terminal. Useful for debugging sleep behavior or when you need direct REPL access.

| Property | Value |
|----------|-------|
| CPU | 240MHz |
| Display | Shows "PYTHON MODE / 240MHz REPL" |
| Sleep timers | Disabled (main loop has exited) |
| Exit | Ctrl+D in REPL (soft reboot, re-runs `main.py`) |

Python mode has no idle timeout and no automatic sleep. It is intended for debugging sessions while connected to USB.

## Routine Interaction

When a routine finishes, `zri.done()` blanks the screen and waits up to 60 seconds for a button press. If no button is pressed, it returns to the launcher, which resumes its own idle timer. The flow is:

```
Routine ends -> done() waits 60s -> returns to launcher -> 30s idle -> Dark -> 10s -> Deep Sleep
```

Total worst case from routine end to deep sleep: ~100 seconds. In practice the performer usually presses a button during `done()`, which brings the launcher back to Active with a fresh idle timer.

## Timings Reference

| Constant | Value | Location |
|----------|-------|----------|
| `IDLE_TIMEOUT_MS` | 30,000ms | `main.py` |
| `SLEEP_GRACE_MS` | 10,000ms | `main.py` |
| `INPUT_POLL_MS` | 5,000ms | `main.py` |
| `DARK_POLL_MS` | 2,000ms | `main.py` |
| `BATT_INTERVAL` | 300,000ms | `main.py` |
| `done()` timeout | 60,000ms | `zri.py` |
