# Brightness and colour capture attempt 01

User sequence: whole-strip BLUE; brightness 100%, 50%, 25%, 2%, 1%, 100%; whole-strip RED, GREEN, BLUE, WHITE; idle. Slider moved slowly and may have generated intermediate values.

Result: unsuccessful for brightness/colour decoding. The recording contains 46 decoded ATT write/notification values (all 20 bytes with valid XOR), primarily AA 01 power polling, and one 33 01 OFF command at frame 4601. LL_TERMINATE_IND appears at frame 4731. A later CONNECT_IND occurs at frame 7054, followed by repeated LL_VERSION_IND packets; no usable brightness/colour ATT commands were captured. Timestamps are not strictly ordered, so relative times across the reconnect are not reliable.

Do not infer brightness scaling or RGB format from this attempt. The user's observed actions are separate from the recorded protocol evidence.

Next attempt: close phone app, reset sniffer by replugging, start a new recording, then reopen app and make a single colour change. Verify fresh connection traffic and that colour command before continuing the full sequence. Existing raw capture and extracted ATT JSON retained for diagnosis.
