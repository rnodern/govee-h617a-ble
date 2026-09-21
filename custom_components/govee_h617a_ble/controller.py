"""Short-lived BLE operations for a Govee H617A."""

from __future__ import annotations

import asyncio

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import CONTROL_CHARACTERISTIC_UUID, STATUS_CHARACTERISTIC_UUID
from .protocol import (
    brightness_frame,
    parse_power_query_response,
    power_frame,
    power_query_frame,
    whole_strip_color_frame,
)

class GoveeH617AController:
    """Send serialized, short-lived control writes to one H617A."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        self._hass = hass
        self.address = address
        self._lock = asyncio.Lock()

    def _ble_device(self) -> BLEDevice | None:
        return bluetooth.async_ble_device_from_address(self._hass, self.address, True)

    async def _async_connect(self) -> BleakClientWithServiceCache:
        """Connect through Home Assistant's managed Bluetooth stack."""
        device = self._ble_device()
        if device is None:
            raise ConnectionError(
                f"H617A {self.address} is not currently visible to a Home Assistant "
                "Bluetooth adapter"
            )
        try:
            return await establish_connection(
                BleakClientWithServiceCache,
                device,
                device.name or f"H617A {self.address}",
                max_attempts=3,
                ble_device_callback=lambda: self._ble_device() or device,
            )
        except (BleakError, TimeoutError, OSError) as err:
            raise ConnectionError(f"Could not connect to H617A {self.address}: {err}") from err

    async def async_write_frames(self, frames: tuple[bytes, ...]) -> None:
        """Connect once, write ordered frames, then disconnect.

        A Home Assistant light service can include power, colour, and brightness
        together.  Keeping those writes in one BLE connection avoids a slow
        reconnect for each property.
        """
        if not frames:
            return
        async with self._lock:
            client = await self._async_connect()
            try:
                for frame in frames:
                    await client.write_gatt_char(
                        CONTROL_CHARACTERISTIC_UUID, frame, response=False
                    )
                    # Conservative pacing, including time to drain the final
                    # no-response write before disconnect. Hardware test pending.
                    await asyncio.sleep(0.05)
            except (BleakError, TimeoutError, OSError) as err:
                raise ConnectionError(f"H617A command failed: {err}") from err
            finally:
                await client.disconnect()

    async def async_set_power(self, is_on: bool) -> None:
        """Turn the strip on or off."""
        await self.async_write_frames((power_frame(is_on),))

    async def async_set_brightness(self, percent: int) -> None:
        """Set brightness in the device's native percentage scale."""
        await self.async_write_frames((brightness_frame(percent),))

    async def async_set_rgb(self, red: int, green: int, blue: int) -> None:
        """Set a solid whole-strip RGB colour."""
        await self.async_write_frames((whole_strip_color_frame(red, green, blue),))

    async def async_get_power_state(self) -> bool | None:
        """Query the strip's power state using the captured AA 01 exchange."""
        response_received = asyncio.Event()
        state: bool | None = None

        def _notification_handler(_: int, data: bytearray) -> None:
            nonlocal state
            parsed_state = parse_power_query_response(bytes(data))
            if parsed_state is not None:
                state = parsed_state
                response_received.set()

        async with self._lock:
            client = await self._async_connect()
            try:
                await client.start_notify(STATUS_CHARACTERISTIC_UUID, _notification_handler)
                await client.write_gatt_char(
                    CONTROL_CHARACTERISTIC_UUID, power_query_frame(), response=False
                )
                await asyncio.wait_for(response_received.wait(), timeout=1.0)
                return state
            except (BleakError, TimeoutError, OSError) as err:
                raise ConnectionError(f"H617A power query failed: {err}") from err
            finally:
                await client.disconnect()
