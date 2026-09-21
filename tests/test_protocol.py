"""Tests based on verified H617A capture fixtures."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

PROTOCOL_PATH = Path(__file__).parents[1] / "custom_components/govee_h617a_ble/protocol.py"
SPEC = importlib.util.spec_from_file_location("protocol", PROTOCOL_PATH)
assert SPEC and SPEC.loader
protocol = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(protocol)


class ProtocolTest(unittest.TestCase):
    """Verify frames against packets captured from the iOS Govee app."""

    def test_power_frames(self) -> None:
        self.assertEqual(
            protocol.power_frame(False).hex(),
            "3301000000000000000000000000000000000032",
        )
        self.assertEqual(
            protocol.power_frame(True).hex(),
            "3301010000000000000000000000000000000033",
        )

    def test_brightness_frames(self) -> None:
        self.assertEqual(
            protocol.brightness_frame(50).hex(),
            "3304320000000000000000000000000000000005",
        )
        self.assertEqual(
            protocol.brightness_frame(100).hex(),
            "3304640000000000000000000000000000000053",
        )

    def test_whole_strip_colour_frame(self) -> None:
        self.assertEqual(
            protocol.whole_strip_color_frame(255, 0, 0).hex(),
            "33051501ff00000000000000ff7f00000000005d",
        )
        self.assertEqual(
            protocol.whole_strip_color_frame(0, 0, 255).hex(),
            "330515010000ff0000000000ff7f00000000005d",
        )

    def test_power_query_and_response(self) -> None:
        self.assertEqual(
            protocol.power_query_frame().hex(),
            "aa010000000000000000000000000000000000ab",
        )
        self.assertTrue(
            protocol.parse_power_query_response(
                bytes.fromhex("aa010100000000000000000000000000000000aa")
            )
        )
        self.assertFalse(
            protocol.parse_power_query_response(
                bytes.fromhex("aa010000000000000000000000000000000000ab")
            )
        )

    def test_rejects_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            protocol.brightness_frame(0)
        with self.assertRaises(ValueError):
            protocol.whole_strip_color_frame(256, 0, 0)

