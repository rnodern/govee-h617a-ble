"""Constants for the Govee H617A BLE integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "govee_h617a_ble"
PLATFORMS: Final = ["light"]

CONF_ADDRESS: Final = "address"
CONF_NAME: Final = "name"
MODEL: Final = "H617A"

SERVICE_UUID: Final = "00010203-0405-0607-0809-0a0b0c0d1910"
STATUS_CHARACTERISTIC_UUID: Final = "00010203-0405-0607-0809-0a0b0c0d2b10"
CONTROL_CHARACTERISTIC_UUID: Final = "00010203-0405-0607-0809-0a0b0c0d2b11"

