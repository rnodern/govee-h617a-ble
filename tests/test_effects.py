"""Capture integrity and async behaviour tests using a fake HA/BLE boundary."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch, AsyncMock

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / 'custom_components/govee_h617a_ble'


def module(name, **attrs):
    result = types.ModuleType(name)
    result.__dict__.update(attrs)
    return result


class Entity:
    async def async_added_to_hass(self): pass
    async def async_will_remove_from_hass(self): pass
    def async_write_ha_state(self): pass


class Modes:
    RGB = 'rgb'
    BRIGHTNESS = 'brightness'


class Client:
    pass


class BleakError(Exception):
    pass


def load_modules():
    package = module('scene_test_component', GoveeH617AConfigEntry=object)
    package.__path__ = [str(COMPONENT)]
    stubs = {
        'scene_test_component': package,
        'homeassistant': module('homeassistant'),
        'homeassistant.components': module('homeassistant.components'),
        'homeassistant.components.light': module('homeassistant.components.light',
            ATTR_BRIGHTNESS='brightness', ATTR_EFFECT='effect', ATTR_RGB_COLOR='rgb_color',
            EFFECT_OFF='off', ColorMode=Modes, LightEntity=Entity,
            LightEntityFeature=types.SimpleNamespace(EFFECT=4)),
        'homeassistant.components.bluetooth': module('homeassistant.components.bluetooth'),
        'homeassistant.config_entries': module('homeassistant.config_entries', ConfigEntry=object),
        'homeassistant.const': module('homeassistant.const', Platform=types.SimpleNamespace(LIGHT='light')),
        'homeassistant.core': module('homeassistant.core', HomeAssistant=object),
        'homeassistant.exceptions': module('homeassistant.exceptions', HomeAssistantError=RuntimeError),
        'homeassistant.helpers': module('homeassistant.helpers'),
        'homeassistant.helpers.entity': module('homeassistant.helpers.entity', DeviceInfo=dict),
        'bleak': module('bleak'),
        'bleak.backends': module('bleak.backends'),
        'bleak.backends.device': module('bleak.backends.device', BLEDevice=object),
        'bleak.exc': module('bleak.exc', BleakError=BleakError),
        'bleak_retry_connector': module('bleak_retry_connector',
            BleakClientWithServiceCache=Client, establish_connection=AsyncMock()),
    }
    loaded = {}
    with patch.dict(sys.modules, stubs):
        for name in ('const', 'protocol', 'scenes', 'controller', 'light'):
            full = 'scene_test_component.' + name
            spec = importlib.util.spec_from_file_location(full, COMPONENT / (name + '.py'))
            m = importlib.util.module_from_spec(spec)
            sys.modules[full] = m
            spec.loader.exec_module(m)
            loaded[name] = m
    return loaded


mods = load_modules()
scenes = mods['scenes'].SCENE_FRAMES
protocol = mods['protocol']


class CaptureTest(unittest.TestCase):
    def test_batch_capture_exposes_every_named_scene(self):
        expected = {
            'Sunrise', 'Sunset', 'Forest', 'Aurora', 'Lightning-A', 'Lightning-B',
            'Starry Sky', 'Spring', 'Summer', 'Fall', 'Winter', 'Rainbow', 'Fire',
            'Wave', 'Deep Sea', 'Karst Cave', 'Glacier', 'Gobi Desert', 'Moonlight',
            'Flower Field', 'Downpour', 'Sunny', 'Volcano-A', 'Volcano-B',
            'Cornfield', 'Meteor shower', 'Flying', 'Tree Shadow', 'Cherry blossoms',
            'Stream', 'Ripple', 'Desert B', 'Sand Grains', 'Aurora B',
        }
        self.assertEqual(set(scenes), expected)
        for name, frames in scenes.items():
            self.assertTrue(frames, name)
            self.assertTrue(all(protocol.verify_frame(frame) for frame in frames), name)
            self.assertTrue(frames[-1].startswith(bytes.fromhex('330504')), name)
            upload = frames[:-1]
            if upload:
                self.assertEqual(upload[0][3], len(upload), name)
                self.assertEqual([f[1] for f in upload], list(range(len(upload) - 1)) + [255], name)

    def test_all_effects_exactly_match_audited_fixtures(self):
        for slug, number in [('sunrise',1), ('starry-sky',2), ('fire',4)]:
            data = json.loads((ROOT / f'captures/h617a-scene-{slug}-session-{number:02}.json').read_text())
            expected = data.get('multi_packet_scene_data', []) + [data['activation']['payload_hex']]
            frames = scenes[data['scene']]
            self.assertEqual([f.hex() for f in frames], expected)
            self.assertTrue(all(protocol.verify_frame(f) for f in frames))
            self.assertTrue(frames[-1].startswith(bytes.fromhex('330504')))
            self.assertFalse(any(f.startswith(bytes.fromhex('3309')) for f in frames))
            upload = frames[:-1]
            if upload:
                self.assertEqual(upload[0][3], len(upload))
                self.assertEqual([f[1] for f in upload], list(range(len(upload)-1)) + [255])
        self.assertNotEqual(scenes['Fire'][-2][2:-1], bytes(17))


class BehaviourTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.calls = []
        self.controller = types.SimpleNamespace(async_write_frames=AsyncMock(side_effect=self.record),
            async_get_power_state=AsyncMock(return_value=True))
        entry = types.SimpleNamespace(data={'address':'AA:BB:CC:DD:EE:FF', 'name':'Test'})
        self.light = mods['light'].GoveeH617ALight(entry, self.controller)
        self.light.hass = types.SimpleNamespace(async_create_task=asyncio.create_task)
        self.light._COMMAND_DEBOUNCE_SECONDS = 0
        self.light._is_on = True

    async def record(self, frames): self.calls.append(frames)

    async def test_effect_ignores_stale_rgb_and_brightness(self):
        await self.light.async_turn_on(rgb_color=(255,0,0), brightness=50)
        await self.light.async_turn_on(effect='Starry Sky', rgb_color=(255,0,0))
        self.assertEqual(self.calls[-1], scenes['Starry Sky'])
        self.assertEqual(self.light.effect, 'Starry Sky')
        self.assertIsNone(self.light.brightness)
        self.assertIsNone(self.light.rgb_color)

    async def test_same_colour_exits_scene(self):
        await self.light.async_turn_on(rgb_color=(255,0,0))
        await self.light.async_turn_on(effect='Fire')
        await self.light.async_turn_on(rgb_color=(255,0,0))
        self.assertEqual(self.calls[-1], (protocol.whole_strip_color_frame(255,0,0),))
        self.assertEqual(self.light.effect, 'off')

    async def test_effect_off_restores_solid(self):
        await self.light.async_turn_on(rgb_color=(0,0,255))
        await self.light.async_turn_on(effect='Fire')
        await self.light.async_turn_on(effect='off')
        self.assertEqual(self.calls[-1], (protocol.whole_strip_color_frame(0,0,255),))

    async def test_off_then_scene_has_one_transaction(self):
        self.light._is_on = False
        await self.light.async_turn_on(effect='Fire')
        self.assertEqual(self.calls, [(protocol.power_frame(True), *scenes['Fire'])])

    async def test_explicit_brightness_does_not_reupload_effect(self):
        await self.light.async_turn_on(effect='Fire')
        await self.light.async_turn_on(brightness=128)
        self.assertEqual(self.calls[-1], (protocol.brightness_frame(50),))
        self.assertEqual(self.light.effect, 'Fire')

    async def test_change_during_upload_waits_and_latest_wins(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def blocked(frames):
            self.calls.append(frames)
            if len(self.calls) == 1:
                entered.set()
                await release.wait()
        self.controller.async_write_frames.side_effect = blocked
        first = asyncio.create_task(self.light.async_turn_on(effect='Fire'))
        await entered.wait()
        second = asyncio.create_task(self.light.async_turn_on(effect='Sunrise'))
        third = asyncio.create_task(self.light.async_turn_on(effect='Starry Sky'))
        await asyncio.sleep(0)
        release.set()
        await asyncio.gather(first, second, third)
        self.assertEqual(self.calls, [scenes['Fire'], scenes['Starry Sky']])

    async def test_failure_surfaces_and_retry_is_complete(self):
        self.controller.async_write_frames.side_effect = ConnectionError('mid-upload failure')
        with self.assertLogs(mods['light']._LOGGER, level='WARNING'):
            with self.assertRaisesRegex(RuntimeError, 'mid-upload'):
                await self.light.async_turn_on(effect='Fire')
        self.assertIsNone(self.light.effect)
        self.controller.async_write_frames.side_effect = self.record
        await self.light.async_turn_on(effect='Fire')
        self.assertEqual(self.calls[-1], (protocol.power_frame(True), *scenes['Fire']))

    async def test_invalid_effect_never_writes(self):
        with self.assertRaises(RuntimeError): await self.light.async_turn_on(effect='Unknown')
        self.assertEqual(self.calls, [])

    async def test_unavailable_startup_schedules_backoff_retry(self):
        self.controller.async_get_power_state.return_value = None
        await self.light.async_added_to_hass()
        await self.light._startup_task
        self.assertFalse(self.light._attr_available)
        self.assertIsNotNone(self.light._retry_task)
        self.assertFalse(self.light._retry_task.done())
        await self.light.async_will_remove_from_hass()

    async def test_unload_cancels_active_upload(self):
        entered = asyncio.Event()
        async def wait_forever(frames):
            entered.set()
            await asyncio.Future()
        self.controller.async_write_frames.side_effect = wait_forever
        action = asyncio.create_task(self.light.async_turn_on(effect='Fire'))
        await entered.wait()
        await self.light.async_will_remove_from_hass()
        with self.assertRaises(asyncio.CancelledError): await action

    async def test_controller_serializes_complete_uploads(self):
        controller = mods['controller'].GoveeH617AController(None, 'test')
        client = types.SimpleNamespace(write_gatt_char=AsyncMock(), disconnect=AsyncMock())
        controller._async_connect = AsyncMock(return_value=client)
        await asyncio.gather(controller.async_write_frames(scenes['Starry Sky']),
                             controller.async_write_frames((protocol.power_frame(False),)))
        sent = [c.args[1] for c in client.write_gatt_char.call_args_list]
        self.assertEqual(sent, [*scenes['Starry Sky'], protocol.power_frame(False)])
        self.assertEqual(client.disconnect.await_count, 2)


if __name__ == '__main__': unittest.main()
