# Govee H617A BLE

A local Home Assistant custom integration for the Govee H617A RGBIC LED strip.

The integration uses Bluetooth Low Energy directly. It exposes one `light` entity
with power, brightness, and RGB colour controls. No Govee cloud account or API key
is required.

## Current status

The H617A protocol was captured from the iOS Govee app and replayed successfully
on the development strip. Power, RGB, brightness, and effects work locally;
state shown after a command is still write-confirmed rather than device readback.
Individual segment editing is not included.

## Experimental effects

Version 0.3.1 includes 34 captured effects: Sunrise, Sunset, Forest, Aurora,
Lightning-A, Lightning-B, Starry Sky, Spring, Summer, Fall, Winter, Rainbow,
Fire, Wave, Deep Sea, Karst Cave, Glacier, Gobi Desert, Moonlight, Flower Field,
Downpour, Sunny, Volcano-A, Volcano-B, Cornfield, Meteor shower, Flying, Tree
Shadow, Cherry blossoms, Stream, Ripple, Desert B, Sand Grains, and Aurora B.

Open the light's controls and select an effect from the Effects list.
Select the `off` effect to return to the last solid colour (white if none is known),
or send a new RGB colour. The `off` effect stops animation; the power toggle turns
the light off. The app should be closed during initial testing.

Each scene uploads in one BLE connection. Pending slider changes are coalesced
and wait for that upload to finish. Brightness is only sent when explicitly
requested, so selecting Sunrise does not resend a stale brightness setting.
Brightness adjustment during effects is experimental too.

Effects can also be selected in automations with `light.turn_on`, for example:

```yaml
action: light.turn_on
target:
  entity_id: light.your_h617a
data:
  effect: Starry Sky
```

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

This version queries power state when it starts. If the strip is busy—for example,
because the Govee app is connected—it retries after 15 seconds and then with a
bounded backoff up to five minutes. Other state represents commands successfully
written by Home Assistant, not confirmed device readback. Entering an effect
clears the reported solid colour and brightness rather than displaying stale
values. Effect identity is unknown after restart. Physical-button/app state
synchronization, transitions, and individual segments remain future work.

## Protocol evidence

Captured evidence and notes are kept in `captures/`. Capture files are ignored by
Git because they include Bluetooth addresses and nearby advertising traffic.

## Development checks

Run the protocol tests and command-behaviour tests (fake HA/BLE boundaries):

```sh
python3 -m unittest discover -s tests
```

## License

MIT. See [LICENSE](LICENSE).
