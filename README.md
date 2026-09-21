# Govee H617A BLE

A local Home Assistant custom integration for the Govee H617A RGBIC LED strip.

The integration uses Bluetooth Low Energy directly. It exposes one `light` entity
with power, brightness, RGB colour controls, and 34 captured effects. An optional
dashboard card adds a DIY Finger Sketch editor. No Govee cloud account or API key
is required.

## Current status

The H617A protocol was captured from the iOS Govee app and replayed successfully
on the development strip. Power, RGB, brightness, and effects work locally;
state shown after a command is still write-confirmed rather than device readback.
The DIY editor supports painting the strip's 15 segments.

## Experimental effects

Version 0.3.2 includes 34 captured effects: Sunrise, Sunset, Forest, Aurora,
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

### DIY editor preview (0.4.0b2)

The optional companion card has a **DIY** button that opens a touch-friendly
Finger Sketch editor: 15 segments, pencil/eraser, undo, background colour or
None, background brightness, six animation types, and speed. Draw first, then
press **Apply to strip** to send one complete pattern. Light controls opens HA's
normal light popup. This does not change the standard popup elsewhere in HA.

The generated encoder matches all 31 controlled capture transactions exactly,
including patterns with a different colour on each of the 15 segments. Both
small patterns and larger multicolour uploads have been tested successfully
on the development H617A. Other devices and firmware versions still need
community testing. Uploads use two to five frames in one connection.
At least one painted segment is required. Background brightness supports
1–100; speed supports 0–100.

To install:

1. Update the integration folder and restart Home Assistant.
2. Copy `www/govee-h617a-card.js` to `/config/www/govee-h617a-card.js`.
   The preview ZIP contains both directories and can be extracted to /config.
3. Add dashboard resource `/local/govee-h617a-card.js?v=0.4.0b2`, type
   **JavaScript module** (Settings → Dashboards → Resources; enable Advanced
   mode in your profile if the Resources menu is hidden).
4. Add a Manual dashboard card using your actual light entity ID:

```yaml
type: custom:govee-h617a-card
entity: light.your_h617a
name: Study strip
```

The editor is an in-memory draft; closing and reopening it keeps unsent edits,
but refreshing the browser discards them. The integration exposes the last
successfully sent DIY pattern as an entity attribute, not device readback.
That pattern is not restored after an HA restart. Named preset saving and
replacement of the standard more-info popup are not part of this preview.
Close the Govee app before applying a pattern.

The same action is available to automations:

```yaml
action: govee_h617a_ble.apply_diy
target:
  entity_id: light.your_h617a
data:
  animation: clockwise
  speed: 0
  background_brightness: 100
  background_rgb: null
  groups:
    - rgb: [0, 0, 255]
      segments: [1]
    - rgb: [0, 255, 0]
      segments: [14]
```

Segment numbers in actions are zero-based; the editor displays 1–15.

### Integration

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
clears the reported solid colour and retains the last selected brightness (full
brightness if none is known). Effect identity is unknown after restart.
Physical-button/app state synchronization and transitions remain future work.

## Protocol development

Bluetooth captures and reverse-engineering notes are kept private. The repository
contains the implementation and protocol tests, without capture artefacts.

## Development checks

Run the protocol tests and command-behaviour tests (fake HA/BLE boundaries):

```sh
python3 -m unittest discover -s tests
```

## License

MIT. See [LICENSE](LICENSE).
