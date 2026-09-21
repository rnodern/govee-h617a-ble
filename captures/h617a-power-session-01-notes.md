# H617A iPhone power capture — 2026-09-21

Local evidence: `h617a-power-session-01.pcap`; extracted application writes and notifications: `h617a-power-session-01.att.json`.
Capture stopped after the user reported completing idle, off, wait, on, wait. Raw capture includes nearby advertisements and device addresses; review/redact before public release.

## Confirmed in this session

- Target advertisement: Govee_H617A_6B4A, matching the working HA scripts.
- 63 extracted ATT write-command/notification values; every value is 20 bytes and has a valid XOR checksum. Captures can contain retransmissions or missing packets; this is not a count of unique app actions.
- Service: 00010203-0405-0607-0809-0a0b0c0d1910.
- Write characteristic: 00010203-0405-0607-0809-0a0b0c0d2b11, handle 0x0014 in this connection.
- Notification characteristic: 00010203-0405-0607-0809-0a0b0c0d2b10, handle 0x0010. Characteristic discovery in frame 5916.
- Off: frame 6928 at 60.367726 s, ATT opcode 0x52, value `3301000000000000000000000000000000000032`.
- On: frame 7339 at 66.518058 s, ATT opcode 0x52, value `3301010000000000000000000000000000000033`.
- Repeated power query: `aa010000000000000000000000000000000000ab`, approximately every three seconds during idle. This demonstrates polling, not that it is required for connection survival.
- Power-query responses distinguish on (`aa0101…aa`) and off (`aa0100…ab`).
- The immediate notification after ON (frame 7342) is `330100…32`, identical to the notification after OFF. Do not interpret this notification as authoritative power state. Subsequent AA 01 response in frame 7426 reports on.
- Discovery indicates the write characteristic supports both write-with-response and write-without-response. The iPhone uses write-without-response for these commands.

## Integration implications

- Use captured 20-byte frames as the app-compatible baseline; retain user-reported working 19-byte power frames as separate compatibility evidence.
- Explicitly select write-without-response, subscribe to the separate status characteristic, and parse query responses separately from command acknowledgements.
- Do not hard-code GATT handles: resolve the characteristic UUIDs.
- Preserve initialisation traffic for later isolation experiments. This capture does not prove which initialisation messages are necessary.
- Brightness, RGB, native scenes, segment mapping, and mandatory heartbeat timing remain unverified.

## Capture setup status

Wireshark 4.6.8 and nRF Util BLE sniffer 0.21.0 installed. Direct Nordic capture succeeds using existing dongle firmware. Wireshark extcap discovery is inconsistent: the interface appears after replugging and disappears on later probing. Temporarily disabling the HCI shim did not resolve it and was reverted. No firmware flashing or ChmodBPF installation performed.
