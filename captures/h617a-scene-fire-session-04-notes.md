# Fire capture — corrected audit

The user observed rapid red/orange/yellow flashes across small LED groups.
The candidate replay is 12 A3 packets followed by
`3305047b08000000000000000000000000000041`.

`33 09 0C 11 26 ...` encodes connection time 12:17:38, not scene selection.
The upload begins `A3 00 01 0C`; 0C matches its 12 packets.
Indices are 00 through 0A, then FF. The FF packet carries meaningful data.

Frames 4859, 4860 and 4862 are explicitly marked as link-layer retransmissions
of final packet 4857. Replay should include that packet once, not four times.
The decoded fixture preserves all of its non-zero data.

Frames 4867/4871 contain A3/33 05 responses. All 57 decoded control writes/status
notifications pass XOR and radio CRC. Standalone replay remains untested.
See [the audit](h617a-scenes-audit.md).
