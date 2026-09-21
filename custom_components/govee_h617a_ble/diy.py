"""Finger Sketch encoding from controlled two- through five-frame captures."""
from .protocol import build_frame

ANIMATIONS = {
    "clockwise": 0x09, "counter_clockwise": 0x0A, "cycle": 0x02,
    "gradient": 0x13, "twinkle": 0x0F, "breathe": 0x14,
}
DIY_EFFECT = "DIY"


def _integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer between {low} and {high}")
    return value


def _rgb(value):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("Colours must have three RGB values")
    return [_integer(v, 0, 255, "RGB") for v in value]


def finger_sketch_frames(animation, speed, background_brightness, background_rgb, groups):
    """Encode a complete pattern using the captured multipart framing.

    Group order is preserved so generated frames can match captures exactly.
    Positions are zero-based. None means the app's no-background sentinel.
    """
    if not isinstance(animation, str) or animation not in ANIMATIONS:
        raise ValueError("Unknown DIY animation")
    speed = _integer(speed, 0, 100, "Speed")
    brightness = _integer(background_brightness, 1, 100, "Background brightness")
    background = [1, 1, 1] if background_rgb is None else _rgb(background_rgb)
    if not isinstance(groups, (list, tuple)) or not 1 <= len(groups) <= 15:
        raise ValueError("Paint at least one segment")
    payload = [ANIMATIONS[animation], speed, brightness, *background, len(groups)]
    seen = set()
    for group in groups:
        if not isinstance(group, dict) or set(group) != {"rgb", "segments"}:
            raise ValueError("Each group requires rgb and segments")
        rgb = _rgb(group["rgb"])
        segments = group["segments"]
        if not isinstance(segments, (list, tuple)) or not 1 <= len(segments) <= 15:
            raise ValueError("Each colour group needs painted segments")
        for segment in segments:
            _integer(segment, 0, 14, "Segment")
            if segment in seen:
                raise ValueError("A segment cannot be assigned more than once")
            seen.add(segment)
        payload.extend([len(segments), *rgb, *segments])
    # First frame reserves three data bytes for the upload header. Later
    # frames hold 17 payload bytes. Even small uploads have a final FF frame.
    chunks = [payload[i:i + 17] for i in range(14, len(payload), 17)] or [[]]
    frames = [build_frame(
        0x00, [0x01, 1 + len(chunks), 0x03, *payload[:14]], frame_type=0xA3
    )]
    for index, chunk in enumerate(chunks, start=1):
        sequence = 0xFF if index == len(chunks) else index
        frames.append(build_frame(sequence, chunk, frame_type=0xA3))
    frames.append(build_frame(0x05, [0x0A, 0x20, 0x03]))
    return tuple(frames)
