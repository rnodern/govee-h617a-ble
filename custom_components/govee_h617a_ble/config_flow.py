"""Config flow for Govee H617A BLE."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_ADDRESS, CONF_NAME, DOMAIN, MODEL


class GoveeH617ABleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle Bluetooth discovery for an H617A."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Allow setup using a known Bluetooth address."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS].upper()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Govee {MODEL} {address[-5:].replace(':', '')}",
                data={CONF_ADDRESS: address, CONF_NAME: f"Govee {MODEL}"},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): str}),
        )

    async def async_step_bluetooth(self, discovery_info: bluetooth.BluetoothServiceInfoBleak) -> FlowResult:
        """Set up from a Bluetooth advertisement."""
        if not discovery_info.connectable:
            return self.async_abort(reason="not_connectable")
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._address = discovery_info.address.upper()
        self._name = discovery_info.name or f"Govee {MODEL}"
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(self, user_input: dict | None = None) -> FlowResult:
        """Confirm adding the discovered strip."""
        if user_input is None:
            return self.async_show_form(step_id="bluetooth_confirm")
        return self.async_create_entry(
            title=self._name,
            data={CONF_ADDRESS: self._address, CONF_NAME: self._name},
        )
