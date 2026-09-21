"""Light entity with atomic scene uploads and coalesced slider commands."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_EFFECT, ATTR_RGB_COLOR, EFFECT_OFF,
    ColorMode, LightEntity, LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo

from . import GoveeH617AConfigEntry
from .const import CONF_ADDRESS, CONF_NAME, DOMAIN, MODEL
from .controller import GoveeH617AController
from .protocol import brightness_frame, power_frame, whole_strip_color_frame
from .scenes import SCENE_FRAMES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry: GoveeH617AConfigEntry, async_add_entities) -> None:
    """Set up the H617A light entity."""
    async_add_entities([GoveeH617ALight(entry, entry.runtime_data)])


class GoveeH617ALight(LightEntity):
    """A locally controlled H617A with experimental captured effects."""

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = [EFFECT_OFF, *SCENE_FRAMES]
    _attr_should_poll = False
    _COMMAND_DEBOUNCE_SECONDS = 0.25
    _AVAILABILITY_RETRY_INITIAL_SECONDS = 15
    _AVAILABILITY_RETRY_MAX_SECONDS = 300

    def __init__(self, entry: ConfigEntry, controller: GoveeH617AController) -> None:
        self._controller = controller
        self._is_on: bool | None = None
        self._brightness: int | None = None
        self._rgb_color: tuple[int, int, int] | None = None
        self._effect: str | None = None
        self._last_solid_rgb = (255, 255, 255)
        self._pending: dict[str, Any] = {}
        self._waiters: list[asyncio.Future[None]] = []
        self._command_task: asyncio.Task | None = None
        self._startup_task: asyncio.Task | None = None
        self._retry_task: asyncio.Task | None = None
        self._removing = False
        self._attr_available = False
        self._attr_unique_id = entry.data[CONF_ADDRESS].replace(":", "").lower()
        self._attr_name = entry.data[CONF_NAME]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_ADDRESS].lower())},
            manufacturer="Govee", model=MODEL, name=entry.data[CONF_NAME],
        )

    @property
    def is_on(self) -> bool | None:
        return self._is_on

    @property
    def brightness(self) -> int | None:
        return self._brightness

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return self._rgb_color

    @property
    def effect(self) -> str | None:
        """Last successfully commanded effect, not device-confirmed readback."""
        return self._effect

    @property
    def color_mode(self) -> ColorMode:
        return ColorMode.BRIGHTNESS if self._effect in SCENE_FRAMES else ColorMode.RGB

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._startup_task = self.hass.async_create_task(self._async_refresh_power_state())

    async def _async_refresh_power_state(self) -> None:
        try:
            self._is_on = await self._controller.async_get_power_state()
            self._attr_available = self._is_on is not None
        except Exception:
            _LOGGER.warning("Could not read H617A initial power state", exc_info=True)
            self._attr_available = False
        if not self._attr_available:
            self._async_schedule_availability_retry()
        if not self._removing:
            self.async_write_ha_state()

    def _async_schedule_availability_retry(self) -> None:
        """Retry a failed probe without repeatedly competing for BLE."""
        if self._removing or (self._retry_task and not self._retry_task.done()):
            return
        self._retry_task = self.hass.async_create_task(
            self._async_retry_until_available()
        )

    async def _async_retry_until_available(self) -> None:
        """Recover after an occupied strip/app connection with bounded backoff."""
        delay = self._AVAILABILITY_RETRY_INITIAL_SECONDS
        while not self._removing and not self._attr_available:
            await asyncio.sleep(delay)
            if self._removing:
                return
            await self._async_refresh_power_state()
            delay = min(delay * 2, self._AVAILABILITY_RETRY_MAX_SECONDS)

    async def async_will_remove_from_hass(self) -> None:
        self._removing = True
        tasks = [
            t for t in (self._command_task, self._startup_task, self._retry_task)
            if t and not t.done()
        ]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for waiter in self._waiters:
            if not waiter.done():
                waiter.cancel()
        self._waiters.clear()
        self._pending.clear()
        await super().async_will_remove_from_hass()

    async def _queue_command(self, changes: dict[str, Any]) -> None:
        """Keep latest pending values; callers wait for transport success/errors."""
        if self._removing:
            raise HomeAssistantError("H617A integration is unloading")
        if not changes['power']:
            self._pending.clear()
        if ATTR_EFFECT in changes:
            self._pending.pop(ATTR_RGB_COLOR, None)
            # A new scene owns brightness unless explicitly supplied with it.
            self._pending.pop(ATTR_BRIGHTNESS, None)
        elif ATTR_RGB_COLOR in changes:
            self._pending.pop(ATTR_EFFECT, None)
        self._pending.update(changes)
        waiter = asyncio.get_running_loop().create_future()
        self._waiters.append(waiter)
        if self._command_task is None or self._command_task.done():
            self._command_task = self.hass.async_create_task(self._async_apply_commands())
        await waiter

    async def _async_apply_commands(self) -> None:
        active_waiters: list[asyncio.Future[None]] = []
        try:
            if self._startup_task is not None:
                await self._startup_task
            while self._pending:
                await asyncio.sleep(self._COMMAND_DEBOUNCE_SECONDS)
                changes, self._pending = self._pending, {}
                active_waiters, self._waiters = self._waiters, []
                try:
                    await self._async_apply(changes)
                except Exception as err:
                    # A partial upload leaves mode/power uncertain. The next
                    # explicit effect selection always uploads its whole sequence.
                    self._is_on = None
                    self._effect = None
                    self._brightness = None
                    self._rgb_color = None
                    self._attr_available = False
                    self._async_schedule_availability_retry()
                    _LOGGER.warning("H617A command failed: %s", err, exc_info=True)
                    for waiter in active_waiters:
                        if not waiter.done():
                            waiter.set_exception(HomeAssistantError(f"H617A command failed: {err}"))
                else:
                    self._attr_available = True
                    for waiter in active_waiters:
                        if not waiter.done():
                            waiter.set_result(None)
                active_waiters = []
                if not self._removing:
                    self.async_write_ha_state()
        finally:
            for waiter in active_waiters + self._waiters:
                if not waiter.done():
                    waiter.cancel()
            self._waiters.clear()

    async def _async_apply(self, changes: dict[str, Any]) -> None:
        """Construct one indivisible transaction, publishing state only on success."""
        on = changes['power']
        frames: list[bytes] = []
        effect, rgb, brightness = self._effect, self._rgb_color, self._brightness
        if not on:
            frames.append(power_frame(False))
        else:
            if self._is_on is not True:
                frames.append(power_frame(True))
            if ATTR_EFFECT in changes and changes[ATTR_EFFECT] != EFFECT_OFF:
                effect = changes[ATTR_EFFECT]
                frames.extend(SCENE_FRAMES[effect])
                rgb, brightness = None, None
            elif ATTR_RGB_COLOR in changes or changes.get(ATTR_EFFECT) == EFFECT_OFF:
                rgb = tuple(changes.get(ATTR_RGB_COLOR, self._last_solid_rgb))
                frames.append(whole_strip_color_frame(*rgb))
                effect = EFFECT_OFF
            if ATTR_BRIGHTNESS in changes:
                brightness = changes[ATTR_BRIGHTNESS]
                frames.append(brightness_frame(max(1, round(brightness * 100 / 255))))
        if frames:
            await self._controller.async_write_frames(tuple(frames))
        self._is_on, self._effect = on, effect
        self._rgb_color, self._brightness = rgb, brightness
        if rgb is not None and effect == EFFECT_OFF:
            self._last_solid_rgb = rgb

    async def async_turn_on(self, **kwargs: Any) -> None:
        effect = kwargs.get(ATTR_EFFECT)
        if ATTR_EFFECT in kwargs and effect not in self._attr_effect_list:
            raise HomeAssistantError(f"Unsupported H617A effect: {effect}")
        if kwargs.get(ATTR_BRIGHTNESS) == 0:
            await self.async_turn_off()
            return
        changes = {'power': True}
        if ATTR_EFFECT in kwargs:
            changes[ATTR_EFFECT] = effect
        # Named effects take precedence over a restored RGB value from HA scenes.
        if ATTR_RGB_COLOR in kwargs and effect not in SCENE_FRAMES:
            changes[ATTR_RGB_COLOR] = tuple(kwargs[ATTR_RGB_COLOR])
        if ATTR_BRIGHTNESS in kwargs:
            changes[ATTR_BRIGHTNESS] = kwargs[ATTR_BRIGHTNESS]
        await self._queue_command(changes)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._queue_command({'power': False})
