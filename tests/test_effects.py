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
        for name in ('const', 'protocol', 'scenes', 'diy', 'controller', 'light'):
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
    def test_generated_diy_matches_every_captured_transaction(self):
        transactions = []
        for name in ('h617a-finger-sketch-segments-03.json', 'h617a-finger-sketch-large-04.json'):
            transactions.extend(json.loads((ROOT / 'captures' / name).read_text())['transactions'])
        names = {value: name for name, value in mods['diy'].ANIMATIONS.items()}
        for transaction in transactions:
            decoded = dict(transaction['decoded'])
            decoded['animation'] = names[decoded.pop('effect')]
            if decoded['background_rgb'] == [1, 1, 1]:
                decoded['background_rgb'] = None
            frames = mods['diy'].finger_sketch_frames(**decoded)
            self.assertEqual([f.hex() for f in frames], [f['hex'] for f in transaction['frames']], transaction['action'])

    def test_diy_rejects_invalid_or_unverified_patterns(self):
        valid = dict(animation='breathe', speed=50, background_brightness=100,
                     background_rgb=None, groups=[{'rgb':[255,0,0], 'segments':[0]}])
        invalid = [
            {'speed':True}, {'speed':101}, {'background_brightness':0},
            {'animation':'static'}, {'background_rgb':[256,0,0]},
            {'groups':[]}, {'groups':[{'rgb':[0,0,255], 'segments':[15]}]},
            {'groups':[{'rgb':[0,0,255], 'segments':[0,0]}]},
            {'groups':[{'rgb':[i,0,0], 'segments':[i]} for i in range(16)]},
        ]
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                mods['diy'].finger_sketch_frames(**(valid | changes))

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

    async def test_diy_apply_is_atomic_and_updates_state_after_success(self):
        pattern = dict(animation='breathe', speed=50, background_brightness=100,
                       background_rgb=None, groups=[{'rgb':[255,0,0], 'segments':[0]}])
        self.light._is_on = False
        await self.light.async_apply_diy(**pattern)
        self.assertEqual(self.calls, [(protocol.power_frame(True), *mods['diy'].finger_sketch_frames(**pattern))])
        self.assertEqual(self.light.effect, 'DIY')
        self.assertEqual(self.light.extra_state_attributes['diy_pattern'], pattern)
        self.assertEqual(self.light.color_mode, Modes.BRIGHTNESS)
        await self.light.async_turn_on(effect='Fire')
        self.assertEqual(self.calls[-1], scenes['Fire'])

    async def test_invalid_diy_never_connects(self):
        with self.assertRaises(RuntimeError):
            await self.light.async_apply_diy(animation='unknown')
        self.assertEqual(self.calls, [])

    async def test_large_diy_uses_one_complete_transaction(self):
        fixture = json.loads((ROOT / 'captures/h617a-finger-sketch-large-04.json').read_text())
        transaction = fixture['transactions'][-1]
        pattern = dict(transaction['decoded'])
        pattern.pop('effect')
        pattern.update(animation='clockwise', background_rgb=None)
        await self.light.async_apply_diy(**pattern)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual([f.hex() for f in self.calls[0]], [f['hex'] for f in transaction['frames']])

    async def test_diy_failure_keeps_previous_saved_pattern(self):
        pattern = dict(animation='breathe', speed=50, background_brightness=100,
                       background_rgb=None, groups=[{'rgb':[255,0,0], 'segments':[0]}])
        await self.light.async_apply_diy(**pattern)
        self.controller.async_write_frames.side_effect = ConnectionError('test failure')
        with self.assertLogs(mods['light']._LOGGER, level='WARNING'):
            with self.assertRaises(RuntimeError):
                await self.light.async_apply_diy(**(pattern | {'speed':100}))
        self.assertEqual(self.light._diy_pattern, pattern)
        await self.light.async_will_remove_from_hass()

    async def test_effect_ignores_stale_rgb_and_brightness(self):
        await self.light.async_turn_on(rgb_color=(255,0,0), brightness=50)
        await self.light.async_turn_on(effect='Starry Sky', rgb_color=(255,0,0))
        self.assertEqual(self.calls[-1], scenes['Starry Sky'])
        self.assertEqual(self.light.effect, 'Starry Sky')
        self.assertEqual(self.light.brightness, 50)
        self.assertIsNone(self.light.rgb_color)

    async def test_effect_without_known_brightness_shows_full_slider(self):
        self.light._brightness = None
        await self.light.async_turn_on(effect='Fire')
        self.assertEqual(self.light.brightness, 255)

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
