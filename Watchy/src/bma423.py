"""
bma423.py -- Pure Python I2C driver for BMA423 accelerometer (raw axis reads).
No C extension required. Registers from BMA423 datasheet (BST-BMA423-DS000).
"""

import struct
import time


class BMA423:
    def __init__(self, i2c, addr=0x18):
        self.i2c = i2c
        self.addr = addr
        self._init()

    def _write(self, reg, val):
        self.i2c.writeto_mem(self.addr, reg, bytes([val]))

    def _read(self, reg, n):
        return self.i2c.readfrom_mem(self.addr, reg, n)

    def _init(self):
        chip_id = self._read(0x00, 1)[0]
        if chip_id != 0x13:
            raise RuntimeError(f"BMA423 not found, chip_id=0x{chip_id:02x}")
        self._write(0x7C, 0x00)   # PWR_CONF: disable advanced power save
        self._write(0x7D, 0x04)   # PWR_CTRL: enable accelerometer
        self._write(0x40, 0xA8)   # ACC_CONF: ODR=100Hz, BWP=normal
        self._write(0x41, 0x01)   # ACC_RANGE: +/-4g

    def read_xyz(self):
        """Return (x, y, z) as signed integers in raw counts (+/-4g range)."""
        data = self._read(0x12, 6)
        x = struct.unpack_from('<h', data, 0)[0] >> 4
        y = struct.unpack_from('<h', data, 2)[0] >> 4
        z = struct.unpack_from('<h', data, 4)[0] >> 4
        return x, y, z

    def suspend(self):
        """Lowest power state (~3.5uA). Disables accelerometer."""
        self._write(0x7D, 0x00)  # PWR_CTRL: disable accel
        self._write(0x7C, 0x02)  # PWR_CONF: enable advanced power save

    def resume(self):
        """Wake from suspend. Restores 100Hz operation."""
        self._write(0x7C, 0x00)  # PWR_CONF: disable advanced power save
        self._write(0x7D, 0x04)  # PWR_CTRL: enable accel
        time.sleep_ms(2)
