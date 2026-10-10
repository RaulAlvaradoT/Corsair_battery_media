import os
import sys
import time
import threading
import winreg

from pywinusb import hid
import keyboard
import pystray
from PIL import Image

CORSAIR_VID = 0x1B1C

KNOWN_PIDS = {
    0x0A38: "HS70 Wireless",
    0x0A4F: "HS70 PRO Wireless",
    0x1B27: "VOID Wireless",
    0x0A2B: "VOID Wireless",
    0x0A14: "VOID PRO Wireless",
    0x0A16: "VOID PRO Wireless",
    0x0A1A: "VOID PRO Wireless",
    0x0A55: "VOID ELITE Wireless",
    0x0A51: "VOID ELITE Wireless",
    0x0A3E: "Virtuoso RGB Wireless",
    0x0A40: "Virtuoso RGB Wireless",
    0x0A42: "Virtuoso RGB Wireless",
    0x0A44: "Virtuoso RGB Wireless",
    0x0A5C: "Virtuoso RGB Wireless",
    0x0A64: "Virtuoso RGB Wireless",
}

REPORT_ID = 100
BATTERY_REQUEST_ID = 0xC9

DEVICE_STATES = {
    0: "Disconnected",
    1: "Connected",
    2: "Low battery",
    4: "Fully charged",
    5: "Charging",
}

VOID_BATTERY_MICUP = 128

BATTERY_POLL = 30
MONITOR_INTERVAL = 2
RECONNECT_DELAY = 2
LOW_BATTERY_THRESHOLD = 10

ICON_FILES = {
    "default": "headphones.ico",
    "charging": "battery-charging.ico",
    "full": "battery-wireless.ico",
    "level-10": "battery-wireless.ico",
    "level-9": "battery-wireless-90.ico",
    "level-8": "battery-wireless-80.ico",
    "level-7": "battery-wireless-70.ico",
    "level-6": "battery-wireless-60.ico",
    "level-5": "battery-wireless-50.ico",
    "level-4": "battery-wireless-40.ico",
    "level-3": "battery-wireless-30.ico",
    "level-2": "battery-wireless-20.ico",
    "level-1": "battery-wireless-10.ico",
    "level-0": "battery-wireless-0.ico",
}

AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "CorsairBatteryLevel"


def resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def autostart_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{os.path.abspath(__file__)}"'


def autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY) as key:
            winreg.QueryValueEx(key, AUTOSTART_NAME)
            return True
    except OSError:
        return False


def set_autostart(enabled: bool) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, autostart_command())
        else:
            try:
                winreg.DeleteValue(key, AUTOSTART_NAME)
            except FileNotFoundError:
                pass


class CorsairApp:
    def __init__(self):
        self._running = True
        self._lock = threading.Lock()
        self._tray = None
        self._battery = None
        self._state = None
        self._device_name = "Corsair headset"
        self._low_notified = False
        self._full_notified = False
        self._last_real_battery = None
        self._device = None
        self._out_reports = {}
        self._icon_cache = {}

    # ---------------------------------------------------------------- devices

    def _find_device(self):
        try:
            candidates = hid.HidDeviceFilter(vendor_id=CORSAIR_VID).get_devices()
        except Exception:
            return None, {}

        for dev in candidates:
            if dev.product_id not in KNOWN_PIDS:
                continue
            try:
                dev.open()
            except Exception:
                continue
            try:
                outs = {r.report_id: r for r in dev.find_output_reports()}
            except Exception:
                outs = {}
            if BATTERY_REQUEST_ID in outs:
                return dev, outs
            try:
                dev.close()
            except Exception:
                pass
        return None, {}

    def _open(self) -> bool:
        dev, outs = self._find_device()
        if dev is None:
            return False
        try:
            dev.set_raw_data_handler(self._on_report)
        except Exception:
            try:
                dev.close()
            except Exception:
                pass
            return False
        with self._lock:
            self._device = dev
            self._out_reports = outs
        self._device_name = f"{dev.vendor_name} {KNOWN_PIDS.get(dev.product_id, 'Corsair headset')}".strip()
        return True

    def _drop(self) -> None:
        with self._lock:
            dev = self._device
            self._device = None
            self._out_reports = {}
        if dev is not None:
            try:
                dev.close()
            except Exception:
                pass

    def _send_output(self, report_id: int, payload) -> None:
        report = self._out_reports.get(report_id)
        if report is None:
            return
        size = len(report.get_raw_data())
        data = [report_id] + list(payload)
        data = (data + [0] * size)[:size]
        report.set_raw_data(data)
        report.send()

    # ------------------------------------------------------------------ input

    def _on_report(self, data) -> None:
        if not data or data[0] != REPORT_ID:
            return
        if len(data) >= 2 and data[1] == 1:
            self._send_play_pause()
            return
        if len(data) >= 5:
            raw = data[2]
            battery = raw - VOID_BATTERY_MICUP if raw > VOID_BATTERY_MICUP else raw
            self._update(battery, data[4])

    @staticmethod
    def _send_play_pause() -> None:
        try:
            keyboard.send("play/pause")
        except Exception:
            pass

    # ---------------------------------------------------------------- monitor

    def _monitor_thread(self):
        last_request = 0.0
        while self._running:
            dev = self._device
            if dev is None or not self._is_plugged(dev):
                self._drop()
                self._set_disconnected()
                if not self._open():
                    time.sleep(RECONNECT_DELAY)
                    continue
                last_request = 0.0
            now = time.time()
            if now - last_request >= BATTERY_POLL:
                last_request = now
                try:
                    self._send_output(BATTERY_REQUEST_ID, [0x64])
                except Exception:
                    self._drop()
            time.sleep(MONITOR_INTERVAL)

    @staticmethod
    def _is_plugged(dev) -> bool:
        try:
            return bool(dev.is_plugged())
        except Exception:
            return False

    # ------------------------------------------------------------------ state

    def _state_name(self, state) -> str:
        return DEVICE_STATES.get(state, DEVICE_STATES[1])

    def _icon_key(self, battery, state) -> str:
        if state == 0:
            return "default"
        if state == 4:
            return "full"
        if state == 5:
            return "charging"
        if battery is not None and battery >= 100:
            return "full"
        level = max(0, min(10, (battery or 0) // 10))
        return f"level-{level}"

    def _load_icon(self, battery, state):
        key = self._icon_key(battery, state)
        if key not in self._icon_cache:
            try:
                path = resource_path(os.path.join("icons", ICON_FILES[key]))
                self._icon_cache[key] = Image.open(path).copy()
            except Exception:
                self._icon_cache[key] = Image.new("RGBA", (64, 64), (0, 120, 215, 255))
        return self._icon_cache[key]

    def _tooltip(self, battery, state) -> str:
        name = self._device_name
        if state == 0:
            return f"{name}: {DEVICE_STATES[0]}"
        if state == 4:
            return f"{name}: {DEVICE_STATES[4]} (100%)"
        if state == 5:
            if self._last_real_battery is not None:
                return f"{name}: {DEVICE_STATES[5]} (~{self._last_real_battery}%)"
            return f"{name}: {DEVICE_STATES[5]}"
        if battery is not None and battery >= 100:
            return f"{name}: {DEVICE_STATES[4]} (100%)"
        return f"{name}: {self._state_name(state)} ({battery}%)"

    def _update(self, battery, state) -> None:
        with self._lock:
            self._battery = battery
            self._state = state
            if state != 5 and battery is not None:
                self._last_real_battery = battery
        self._apply_tray(battery, state)
        self._maybe_notify_low(battery, state)
        self._maybe_notify_full(battery, state)

    def _set_disconnected(self) -> None:
        with self._lock:
            self._battery = None
            self._state = 0
        self._apply_tray(None, 0)

    def _apply_tray(self, battery, state) -> None:
        tray = self._tray
        if tray is None:
            return
        try:
            tray.icon = self._load_icon(battery, state)
        except Exception:
            pass
        try:
            tray.title = self._tooltip(battery, state)
        except Exception:
            pass

    def _maybe_notify_low(self, battery, state) -> None:
        if state in (0, 5) or battery is None:
            return
        if battery <= LOW_BATTERY_THRESHOLD:
            if not self._low_notified and self._tray is not None:
                self._low_notified = True
                try:
                    self._tray.notify(f"{self._device_name}: {battery}%", "Battery low")
                except Exception:
                    pass
        elif battery > LOW_BATTERY_THRESHOLD + 5:
            self._low_notified = False

    def _maybe_notify_full(self, battery, state) -> None:
        if battery is None:
            return
        is_full = state == 4 or (state != 5 and battery >= 100)
        if is_full:
            if not self._full_notified and self._tray is not None:
                self._full_notified = True
                try:
                    self._tray.notify(f"{self._device_name}: 100%", "Fully charged — you can unplug")
                except Exception:
                    pass
        elif state != 5 and battery < 95:
            self._full_notified = False

    # ------------------------------------------------------------------- menu

    def _refresh(self) -> None:
        self._drop()

    def _toggle_autostart(self, icon, item) -> None:
        try:
            set_autostart(not autostart_enabled())
        except OSError:
            pass

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("Refresh device", lambda i, o: self._refresh()),
            pystray.MenuItem(
                "Start with Windows",
                self._toggle_autostart,
                checked=lambda item: autostart_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", lambda i, o: i.stop()),
        )

    # -------------------------------------------------------------------- run

    def run(self) -> None:
        try:
            initial_icon = Image.open(resource_path(os.path.join("icons", ICON_FILES["default"]))).copy()
        except Exception:
            initial_icon = Image.new("RGBA", (64, 64), (0, 120, 215, 255))

        self._tray = pystray.Icon(
            "corsair",
            initial_icon,
            "Corsair battery level",
            self._build_menu(),
        )

        threading.Thread(target=self._monitor_thread, name="device-monitor", daemon=True).start()

        self._tray.run()


if __name__ == "__main__":
    CorsairApp().run()
