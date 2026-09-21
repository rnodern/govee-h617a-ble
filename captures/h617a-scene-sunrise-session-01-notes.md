# Sunrise capture — corrected audit

The user observed a slow whole-strip fade from almost off. The earlier labelling
of `33 09` as scene activation was incorrect: its bytes encode the connection's
local time (11:59:20).

The candidate Sunrise selection is frame 2362 at 45.732417 seconds:
`3305040000000000000000000000000000000032`.
Frame 2365 contains `3305000000000000000000000000000000000036` in response.
There is no A3 upload in this recording. All 63 decoded control writes/status
notifications pass both XOR and Nordic radio CRC checks.

Standalone replay remains untested. See [the audit](h617a-scenes-audit.md).
