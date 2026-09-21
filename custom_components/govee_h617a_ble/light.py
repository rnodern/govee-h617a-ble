"""Light entity for the Govee H617A BLE integration."""

from __future__ import annotations

import asyncio

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from . import GoveeH617AConfigEntry
from .const import CONF_ADDRESS, CONF_NAME, DOMAIN, MODEL
from .controller import GoveeH617AController
from .protocol import brightness_frame, power_frame, whole_strip_color_frame


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GoveeH617AConfigEntry,
    async_add_entities,
) -> None:
    """Set up the H617A light entity."""
    async_add_entities([GoveeH617ALight(entry, entry.runtime_data)])


class GoveeH617ALight(LightEntity):
    """A locally controlled Govee H617A light."""

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _attr_should_poll = False
    _COMMAND_DEBOUNCE_SECONDS = 0.25

    def __init__(self, entry: ConfigEntry, controller: GoveeH617AController) -> None:
        """Initialise the light with conservative, unknown-state defaults."""
        self._entry = entry
        self._controller = controller
        self._is_on: bool | None = None
        self._brightness: int | None = None
        self._rgb_color: tuple[int, int, int] | None = None
        self._applied_power: bool | None = None
        self._applied_brightness: int | None = None
        self._applied_rgb: tuple[int, int, int] | None = None
        self._command_pending = False
        self._command_task: asyncio.Task[None] | None = None
        self._attr_available = False
        self._attr_unique_id = entry.data[CONF_ADDRESS].replace(":", "").lower()
        self._attr_name = entry.data[CONF_NAME]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_ADDRESS].lower())},
            manufacturer="Govee",
            model=MODEL,
            name=entry.data[CONF_NAME],
        )

    @property
    def is_on(self) -> bool | None:
        """Return the last confirmed power state, if one is known."""
        return self._is_on

    @property
    def brightness(self) -> int | None:
        """Return brightness in Home Assistant's 0–255 scale."""
        return self._brightness

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the last confirmed RGB colour."""
        return self._rgb_color

    async def async_added_to_hass(self) -> None:
        """Query state once after Home Assistant restores the entity."""
        await super().async_added_to_hass()
        self.hass.async_create_task(self._async_refresh_power_state())

    async def _async_refresh_power_state(self) -> None:
        """Refresh power state without assuming an off default after restart."""
        try:
            state = await self._controller.async_get_power_state()
        except ConnectionError:
            self._attr_available = False
        else:
            self._is_on = state
            self._attr_available = state is not None
            self._applied_power = state
        self.async_write_ha_state()

    def _queue_command(self) -> None:
        """Coalesce rapid picker changes into the most recent device state."""
        self._command_pending = True
        if self._command_task is None or self._command_task.done():
            self._command_task = self.hass.async_create_task(self._async_apply_commands())

    async def _async_apply_commands(self) -> None:
        """Apply the latest desired state without building a BLE backlog."""
        while self._command_pending:
            self._command_pending = False
            await asyncio.sleep(self._COMMAND_DEBOUNCE_SECONDS)

            target_power = self._is_on
            target_brightness = self._brightness
            target_rgb = self._rgb_color
            frames: list[bytes] = []
            if target_power is not None and target_power != self._applied_power:
                frames.append(power_frame(target_power))
            if target_power and target_rgb is not None and target_rgb != self._applied_rgb:
                frames.append(whole_strip_color_frame(*target_rgb))
            if (
                target_power
                and target_brightness is not None
                and target_brightness != self._applied_brightness
            ):
                percent = max(1, round(target_brightness * 100 / 255))
                frames.append(brightness_frame(percent))

            if not frames:
                continue
            try:
                await self._controller.async_write_frames(tuple(frames))
            except ConnectionError:
                self._attr_available = False
            else:
                self._applied_power = target_power
                self._applied_rgb = target_rgb
                self._applied_brightness = target_brightness
                self._attr_available = True
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on and optionally apply RGB and brightness."""
        self._is_on = True
        if ATTR_RGB_COLOR in kwargs:
            red, green, blue = kwargs[ATTR_RGB_COLOR]
            self._rgb_color = (red, green, blue)
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
        self._queue_command()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the strip."""
        self._is_on = False
        self._queue_command()
        self.async_write_ha_state()
