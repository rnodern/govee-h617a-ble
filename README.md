# Govee H617A BLE

A local Home Assistant custom integration for the Govee H617A RGBIC LED strip.

The integration uses Bluetooth Low Energy directly. It exposes one `light` entity
with power, brightness, and RGB colour controls. No Govee cloud account or API key
is required.

## Current status

The H617A protocol in this project was captured from the iOS Govee app and tested
for power, whole-strip RGB colour, and 1–100% brightness. Native scenes and
individual segment control are not included yet.

## Installation during development

Copy `custom_components/govee_h617a_ble` to the same path inside your Home
Assistant configuration directory, restart Home Assistant, then add **Govee H617A
BLE** from Settings → Devices & services.

The strip advertises as `Govee_H617A_XXXX`. The Home Assistant Bluetooth adapter
or Bluetooth proxy must support active connections to it.

## Find the Bluetooth address

Automatic discovery should offer the strip when Home Assistant sees its
`Govee_H617A_XXXX` advertisement. If you add the integration manually, enter the
strip's current Bluetooth address:

1. Power on the strip.
2. In Home Assistant, open **Settings → Devices & services → Bluetooth**.
3. Open **Advertisements**, search for `Govee_H617A`, and copy its address.
4. Add **Govee H617A BLE** and paste that address when prompted.

Do not copy the address from an example or another installation; it belongs to
one physical strip. If the strip is absent from Advertisements, move it closer
to the Home Assistant Bluetooth adapter and power-cycle it, then wait a few
seconds for a new advertisement.

This version queries power state when it starts. RGB colour and brightness show
the last values successfully sent by Home Assistant. Continuous state updates
for physical-button changes, transitions, native scenes, and individual segments
are planned follow-up work.

## Protocol evidence

Captured evidence and notes are kept in `captures/`. Capture files are ignored by
Git because they include Bluetooth addresses and nearby advertising traffic.

## Development checks

Run the dependency-free protocol tests:

```sh
python3 -m unittest discover -s tests
```

## License

MIT. See [LICENSE](LICENSE).
