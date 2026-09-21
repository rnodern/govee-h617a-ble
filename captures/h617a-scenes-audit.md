# Scene capture audit — 2026-09-21

## Decision

Enough evidence exists to implement experimental replay of Sunrise, Starry Sky,
and Fire. Independent Home Assistant replay and arbitrary animation generation
are not yet verified.

## Correction: 33 09 is time synchronization

Earlier notes incorrectly labelled connection initialization as scene selection.
Bytes 2–4 of every 33 09 command match the local time around connection:

| Session | Bytes | Decoded time | Capture timestamp (Melbourne) |
|---|---|---|---|
| Sunrise | 0B 3B 14 | 11:59:20 | 11:59:20.994 |
| Starry Sky | 0C 05 18 | 12:05:24 | 12:05:24.923 |
| Starry Sky repeat | 0C 09 29 | 12:09:41 | 12:09:42.305 |
| Fire | 0C 11 26 | 12:17:38 | 12:17:39.476 |

This strongly indicates clock synchronization. Remaining fields are unassigned.
Do not replay these old timestamps as scene commands.

## Candidate replay sequences

| Scene | A3 packets excluding link retries | Final selection prefix | Evidence |
|---|---:|---|---|
| Sunrise | 0 | 33 05 04 00 00 | One selection, frame 2362 |
| Starry Sky | 5 | 33 05 04 76 08 | Two identical uploads and selections |
| Fire | 12 | 33 05 04 7B 08 | One complete upload and selection |

If the two bytes after 33 05 04 are little-endian identifiers, these are 0, 2166
and 2171. That encoding is an inference; exact captured bytes suffice for replay.
All frames are 20 bytes with XOR checksums.

The first A3 packet starts A3 00 01 followed by a packet count: 05 or 0C.
Interior indices increase sequentially. FF identifies the final packet and can
carry data. Preserve that data and send each packet once.

The first Starry Sky upload spans about 31 ms including selection, the repeat
about 32 ms, and Fire about 91 ms including radio retries. This reflects BLE
connection-event batching, not a proved mandatory application delay. Conservative
write spacing needs replay testing; do not reproduce radio retries as commands.

## Integrity and limits

All 236 decoded control writes/status notifications across four captures pass
both XOR and Nordic radio CRC checks. Two short ATT discovery values in each
recording are not Govee frames and are excluded. Fire's repeated FF packets are
marked btle.retransmit by Wireshark.

The animations continue while recorded app traffic is only periodic AA 01
polling. This supports execution on the controller. It does not establish RAM
versus flash storage, persistence after power loss, or whether polling is needed
to keep an idle connection alive. Palette, segment, and timing fields are not
yet decoded. A short final selection command might use cached data; the first
replay should include the whole captured upload.

A3 and 33 05 responses are observed but their status-byte semantics are not
established. A notification is not proof of successful independent replay.
All captures include app initialization, whose necessity remains untested.

## Implementation and first hardware test

Expose Sunrise, Starry Sky, and Fire as light effects, usable by HA scenes and
automations. Upload A3 packets and final 33 05 selection under one lock and one
connection. No power, RGB, brightness, or polling write should interleave with
an upload. Turn on first if required. Do not resend stale solid RGB values after
selecting an effect: doing so could cancel it.

Use immutable captured sequences rather than a guessed animation encoder. Treat
effect state as last commanded until readback is decoded. Surface write failures
and retry the full upload, not a suffix. Existing background command error
handling and task cancellation on entity unload need work before adding longer
transactions.

With the iPhone app closed, select each effect, confirm its physical pattern,
and switch back to solid RGB. Test Fire -> Starry Sky -> Sunrise, off/on, and a
power-cycle followed by a fresh upload. Start without clock-sync/discovery
queries; add initialization only if testing requires it. A power-cycle test
avoids mistaking cached app data for a successful upload. These physical tests
have not been performed.

## External cross-check

[CodingKiwi's original reverse engineering](https://blog.coding.kiwi/reverse-engineering-govee-smart-lights/)
describes 33 05 04 scene selection and A3 multipart writes for another Govee
model. This corroborates framing, not H617A payload semantics or replay success.
The exact H617A bytes and integrity findings above come from our own captures.
