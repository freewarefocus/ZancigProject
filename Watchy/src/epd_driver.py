"""
epd_driver.py -- SSD1681 e-paper driver for Watchy V3 (GDEY0154D67, 200x200)
Ported from GxEPD2 via MIT reference (Matti Gruener, fab.cba.mit.edu).
Pins hardcoded for Watchy V3 ESP32-S3.
"""

import time
from machine import Pin, SPI

WIDTH = 200
HEIGHT = 200


class EPD:
    def __init__(self):
        self.cs = Pin(33, Pin.OUT, value=1)
        self.dc = Pin(34, Pin.OUT, value=1)
        self.rst = Pin(35, Pin.OUT, value=1)
        self.busy = Pin(36, Pin.IN)
        self.spi = SPI(1, baudrate=4000000, polarity=0, phase=0,
                       sck=Pin(47), mosi=Pin(48))
        self._inited = False

    def send_command(self, cmd):
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytes([cmd]))
        self.cs.value(1)
        self.dc.value(1)

    def send_data(self, data):
        self.dc.value(1)
        self.cs.value(0)
        if isinstance(data, int):
            self.spi.write(bytes([data]))
        else:
            self.spi.write(data)
        self.cs.value(1)

    def reset(self):
        self.rst.value(1)
        time.sleep_ms(10)
        self.rst.value(0)
        time.sleep_ms(10)
        self.rst.value(1)
        time.sleep_ms(10)

    def wait_while_busy(self, timeout_ms=10000):
        start = time.ticks_ms()
        while self.busy.value() == 1:  # HIGH = busy
            time.sleep_ms(1)
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                raise OSError('EPD busy timeout')

    def set_partial_ram_area(self, x, y, w, h):
        self.send_command(0x11)  # data entry mode
        self.send_data(0x03)
        self.send_command(0x44)  # RAM X start/end
        self.send_data(x // 8)
        self.send_data((x + w - 1) // 8)
        self.send_command(0x45)  # RAM Y start/end
        self.send_data(y & 0xFF)
        self.send_data((y >> 8) & 0xFF)
        yend = y + h - 1
        self.send_data(yend & 0xFF)
        self.send_data((yend >> 8) & 0xFF)
        self.send_command(0x4E)  # RAM X counter
        self.send_data(x // 8)
        self.send_command(0x4F)  # RAM Y counter
        self.send_data(y & 0xFF)
        self.send_data((y >> 8) & 0xFF)

    def init(self):
        if self._inited:
            return
        self.reset()
        time.sleep_ms(10)
        self.send_command(0x12)  # soft reset
        self.wait_while_busy(1000)
        self.send_command(0x01)  # driver output control
        self.send_data(0xC7)    # 200-1 = 199 = 0xC7
        self.send_data(0x00)
        self.send_data(0x00)
        self.send_command(0x3C)  # border waveform
        self.send_data(0x02)    # dark border (stealth)
        self.send_command(0x18)  # temperature sensor
        self.send_data(0x80)    # built-in sensor
        self.set_partial_ram_area(0, 0, WIDTH, HEIGHT)
        self._inited = True

    def power_on(self):
        self.send_command(0x22)
        self.send_data(0xE0)
        self.send_command(0x20)
        self.wait_while_busy(5000)

    def power_off(self):
        self.send_command(0x22)
        self.send_data(0x83)
        self.send_command(0x20)
        self.wait_while_busy(2000)

    def write_image(self, x, y, w, h, buf):
        if not self._inited:
            self.init()
        self.set_partial_ram_area(x, y, w, h)
        self.send_command(0x24)  # write RAM (BW)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(buf)
        self.cs.value(1)

    def write_image_both(self, x, y, w, h, buf):
        """Write buffer to both BW (0x24) and RED (0x26) RAM.
        Required for clean partial refresh -- SSD1681 compares old vs new."""
        if not self._inited:
            self.init()
        self.set_partial_ram_area(x, y, w, h)
        self.send_command(0x24)  # write RAM (BW / new)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(buf)
        self.cs.value(1)
        self.set_partial_ram_area(x, y, w, h)
        self.send_command(0x26)  # write RAM (RED / old)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(buf)
        self.cs.value(1)

    def write_image_prev(self, x, y, w, h, buf):
        """Write buffer to RED (0x26) RAM only -- update baseline for next partial."""
        if not self._inited:
            self.init()
        self.set_partial_ram_area(x, y, w, h)
        self.send_command(0x26)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(buf)
        self.cs.value(1)

    def update_full(self):
        self.send_command(0x22)
        self.send_data(0xF7)
        self.send_command(0x20)
        self.wait_while_busy(20000)

    def update_partial(self):
        self.send_command(0x22)
        self.send_data(0xFF)  # self-contained: enable, load LUT, display, disable
        self.send_command(0x20)
        self.wait_while_busy(5000)

    def sleep(self):
        self.power_off()
        self.send_command(0x10)  # deep sleep
        self.send_data(0x01)
        self._inited = False     # next use requires re-init after deep sleep
