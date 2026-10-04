# Assembly and variants

The default native voice layouts are female1 Thomas (1012Hz) and active 1414.
All five Thomas populations and all thirteen active populations use their own
complete BOM under `variants/`. A BOM changes population, never connector order.
Stamp the fitted body/pitch or corner/sweet/allowed windows on the board; the
default native silkscreen is valid only for the default population. For another
population, edit that text before producing manufacturing artwork.

The active cards for the original pitches, in body order, are 1414, 4000, 8000,
250, 500. Program the matching `eeprom.json` with a unique serial number after
temporarily bridging JSID1. Remove the bridge and verify write protection.
The JSON templates are deliberately not programmer-ready binary images: the
firmware-5 storage/termination protocol and unique serial assignment must be
agreed before programming hardware. Maximum capacity is 256 bytes.

Fit gold-plated contacts on both halves. Remove male pin 14/24 and block the
matching socket cavity. Sockets are on B.Cu; all small parts are on F.Cu.
Use insulated M3 standoffs. Do not hot-plug any card. Verify contact numbering
with a meter before fitting silicon. Direct analyser JSRC1 defaults to pins
1-2 (HARNESS); pins 2-3 select the bench JST. All attenuation bypasses are OPEN.

The 5V backplane rail, USB-derived MEGA_5V and IOREF are distinct supplies.
Follow REVIEW.md and SHIELDS.md section 13 for continuity and power-up checks.
Hardware performance, enclosure fit and a fabrication release remain unverified.
