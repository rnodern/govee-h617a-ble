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

This first version reports the state it last successfully sent. A state refresh
after a Home Assistant restart, physical-button changes, transitions, native
scenes, and individual segments are planned follow-up work.

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
