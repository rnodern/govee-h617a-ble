"""Captured Govee H617A BLE packet construction and parsing."""

from __future__ import annotations

from collections.abc import Iterable

FRAME_LENGTH = 20
FRAME_DATA_LENGTH = FRAME_LENGTH - 1
COMMAND_FRAME = 0x33
REQUEST_FRAME = 0xAA

POWER_COMMAND = 0x01
BRIGHTNESS_COMMAND = 0x04
COLOR_COMMAND = 0x05
SEGMENTED_COLOR_MODE = 0x15
WHOLE_STRIP_MASK = (0xFF, 0x7F)


def xor_checksum(data: Iterable[int]) -> int:
    """Return the XOR checksum used by the Govee BLE protocol."""
    checksum = 0
    for value in data:
        checksum ^= value
    return checksum & 0xFF


def build_frame(command: int, payload: Iterable[int] = (), frame_type: int = COMMAND_FRAME) -> bytes:
    """Build a zero-padded 20-byte Govee frame with an XOR checksum."""
    values = [frame_type, command, *payload]
    if len(values) > FRAME_DATA_LENGTH:
        raise ValueError("Govee payload is too long")
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("Govee frame values must be bytes")
    values.extend([0] * (FRAME_DATA_LENGTH - len(values)))
    values.append(xor_checksum(values))
    return bytes(values)


def verify_frame(frame: bytes) -> bool:
    """Return whether a complete captured frame has a valid checksum."""
    return len(frame) == FRAME_LENGTH and xor_checksum(frame[:-1]) == frame[-1]


def power_frame(is_on: bool) -> bytes:
    """Build the captured power command."""
    return build_frame(POWER_COMMAND, [int(is_on)])


def brightness_frame(percent: int) -> bytes:
    """Build a brightness command using the H617A's 1–100 percentage scale."""
    if not 1 <= percent <= 100:
        raise ValueError("Brightness must be between 1 and 100 percent")
    return build_frame(BRIGHTNESS_COMMAND, [percent])


def whole_strip_color_frame(red: int, green: int, blue: int) -> bytes:
    """Build the captured whole-strip segmented RGB command."""
    rgb = [red, green, blue]
    if any(not 0 <= value <= 0xFF for value in rgb):
        raise ValueError("RGB values must be between 0 and 255")
    return build_frame(
        COLOR_COMMAND,
        [SEGMENTED_COLOR_MODE, 0x01, *rgb, 0, 0, 0, 0, 0, *WHOLE_STRIP_MASK],
    )


def power_query_frame() -> bytes:
    """Build the captured power-state query frame."""
    return build_frame(POWER_COMMAND, frame_type=REQUEST_FRAME)


def parse_power_query_response(frame: bytes) -> bool | None:
    """Parse an AA 01 power-query response, otherwise return None."""
    if not verify_frame(frame) or frame[:2] != bytes([REQUEST_FRAME, POWER_COMMAND]):
        return None
    if frame[2] not in (0, 1):
        return None
    return bool(frame[2])

