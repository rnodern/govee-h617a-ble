# Verified H617A colour and brightness — 2026-09-21

Capture: `h617a-color-check-02.pcap`. Recording stopped after user confirmed brightness sequence. Extracted ATT values: `h617a-color-check-02.att.json`. Distinct command fixtures: `h617a-verified-color-brightness.json`.

## Whole-strip colour

User selected red, then green, blue, white. Matching writes:

| Selection | Frame | RGB |
|---|---:|---|
| Red | 1223 | 255, 0, 0 |
| Green | 3515 | 0, 255, 0 |
| Blue | 3862 | 0, 0, 255 |
| White | 4204 | 255, 255, 255 |

All use `33 05 15 01 R G B 00 00 00 00 00 FF 7F 00 00 00 00 00 XOR`, 20 bytes including checksum. The FF 7F mask is confirmed for these whole-strip selections; this alone does not establish the physical segment count or per-segment mapping. White is RGB white; independent colour-temperature control is not established.

## Brightness

User selected 50%, 25%, 1%, 100% with white active. Matching writes:

| Percentage | Frame | Value byte | Checksum |
|---|---:|---|---|
| 50 | 7164 (repeated at 7166) | 32 | 05 |
| 25 | 7597 | 19 | 2E |
| 1 | 7897 | 01 | 36 |
| 100 | 8254 | 64 | 53 |

Hex bytes shown. Format: `33 04 percentage`, 16 zero bytes, XOR checksum. This confirms percentage encoding for these tested settings, rather than a 0–255 raw scale. HA brightness needs conversion to device percentages. Zero-brightness semantics and low-value rounding remain implementation/test decisions.

## Integrity and state

140 decoded write-command/notification values, all 20 bytes. 139 pass XOR; frame 2123 fails XOR and is also flagged by Nordic/Wireshark as a radio CRC error. Exclude that corrupted observation from valid protocol fixtures. All eight distinct colour/brightness command fixtures pass XOR. Duplicate packets are retained in the extraction and deduplicated in the fixtures.

Writes use ATT opcode 0x52, handle 0x0014; notifications use 0x0010. Resolve UUIDs rather than handles in an integration. Power-query exchanges continue through the end of the recording. These captures confirm app commands; replay through Home Assistant remains untested.

Raw captures contain Bluetooth addresses and nearby advertisements. Keep local and review/redact before publishing.
