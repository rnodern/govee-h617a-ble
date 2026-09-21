# Starry Sky captures — corrected audit

Sessions 02 and 03 contain identical five-packet A3 uploads, each followed by
`330504760800000000000000000000000000004c`. This is the candidate replay
sequence. The user observed blue with small groups flashing white/cyan.

The earlier interpretation of `33 09` as scene selection was incorrect.
`0C 05 18` and `0C 09 29` encode 12:05:24 and 12:09:41, matching connection times.

The upload starts `A3 00 01 05`; 05 matches its five packets.
Indices are 00, 01, 02, 03, FF. FF marks the last packet and can carry data;
Starry Sky's final payload happens to be zero.

Both sessions contain A3 and 33 05 responses. Their status semantics are not
verified, and neither proves standalone replay works. All 59/57 decoded
control writes/status notifications pass XOR and radio CRC.
See [the audit](h617a-scenes-audit.md).
