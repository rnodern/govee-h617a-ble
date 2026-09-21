# Finger Sketch controlled capture

Source: local `h617a-finger-sketch-segments-03.pcap`. Sanitized commands,
frame references, user action labels, and decoded values are in
`h617a-finger-sketch-segments-03.json`. Raw radio traffic stays untracked.

All 50 recorded control frames pass 20-byte length and XOR checks. Two adjacent
identical upload repeats are omitted from the fixture, leaving 16 transactions
of two A3 frames plus one activation. All decoded groups consume their payload
exactly apart from zero padding. These are app captures; subsequent generated
command hardware validation is recorded below.

## Observed framing

First frame: `A3 00 01 02 03` followed by 14 payload bytes and XOR checksum.
Final frame: `A3 FF` followed by 17 payload bytes including padding, then XOR.
Activation: `33050a200300000000000000000000000000001f`.

Every upload in capture 03 uses two frames. The `02` gives the frame count;
capture 04 confirms larger Finger Sketch uploads below.
The meaning of the other constant header/activation fields is not established.

## Reassembled payload

Offsets below start after the five-byte first-frame header. Append final-frame
bytes 2 through 18 (zero-based), excluding both checksums.

| Offset | Meaning | Evidence |
| --- | --- | --- |
| 0 | Animation ID | Six isolated effect selections |
| 1 | Speed | 0, 48, 100 |
| 2 | Background brightness | 100 to 50 with red background |
| 3–5 | Background RGB | Red FF0000, blue 0000FF, none 010101 |
| 6 | Number of painted colour groups | Two to three and back |
| 7 onward | Repeated groups | Count, R, G, B, then count segment indices |

Group order is not spatial: when blue was introduced, its group followed the
existing red and green groups. Segment indices explicitly identify positions.
Leftmost is 0, second is 1, rightmost is 14; the earlier all-red capture lists
0 through 14. This describes 15 app segments, not individual LED counts.
Erasing removes a segment from its painted group. Background RGB is separate
even when it matches a painted group's RGB. `010101` is the observed app
encoding of no background; broader firmware sentinel behaviour is untested.

| Animation | Hex ID |
| --- | --- |
| Clockwise | 09 |
| Counter Clockwise | 0A |
| Cycle | 02 |
| Gradient | 13 |
| Twinkle | 0F |
| Breathe | 14 |

## Larger upload confirmation (capture 04)

The controlled large-pattern capture adds one distinct colour at a time from
one through fifteen painted segments. Its 15 sanitized transactions are in
`h617a-finger-sketch-large-04.json`. Each included frame passes the Nordic
radio CRC and application XOR checks. Adjacent identical repeats and a damaged
first packet at frame 24289 are excluded; frame 24291 supplies the clean copy.

The first packet carries 14 payload bytes; subsequent packets carry 17.
The first header's byte 3 gives the upload packet count. Sequence bytes are
00, 01, 02, etc., with FF replacing the final sequence number.
There are always at least two upload frames, even for a one-colour pattern.
Activation remains `33050a200300000000000000000000000000001f`.

Observed distinct-colour counts and upload sizes:

| Colour groups (one segment each) | Upload frames |
| --- | --- |
| 1–4 | 2 |
| 5–8 | 3 |
| 9–11 | 4 |
| 12–15 | 5 |

The encoder reproduces all 31 transactions from captures 03 and 04 byte-for-byte.
The user confirmed both the two-frame editor preview and the larger generated
uploads in version 0.4.0b2 work on their H617A.

## Remaining limits

Empty-pattern behaviour, brightness zero, and a true static mode remain
unverified. This format is not a full decoder for built-in scene payloads or
all features of the DIY tab. Hardware confirmation is from one development
H617A; broader firmware compatibility needs community testing.
