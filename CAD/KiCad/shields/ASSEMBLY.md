# Assembly and variants

The default native voice layouts are female1 Thomas (1012Hz) and active 1414.
All five Thomas populations and all thirteen active populations use their own
complete BOM under `variants/`. A BOM changes population, never connector order.
Mark the fitted body or corner in the front white box and tick its row in the
back silkscreen table. The same artwork supports every population. The
population.json files describe assembly choices; no memory chip is fitted.

Build in this order: (1) backplane, five Thomas cards and MSGEQ7 analyser with
Mega/firmware 4; (2) Teensy adapter with analyser slot empty; (3) active cards
1414, 4000, 8000, 250, 500 in body order. Other corners come later as needed.

Fit gold-plated contacts on both halves. Remove male pin 6/22 and block the
matching socket cavity. Sockets are on B.Cu. Small parts are on F.Cu except the five Teensy
input capacitors CM1-CM5, on B.Cu beside the microphone socket pins.
Use insulated M3 standoffs. Do not hot-plug any card. Verify contact numbering
with a meter before fitting silicon. All MSGEQ7 attenuation bypasses are OPEN.
Leave JA1 empty with the Teensy. MIC DIRECT pads read the microphone bias.

The 5V backplane rail, USB-derived MEGA_5V and IOREF are distinct supplies.
Follow REVIEW.md and SHIELDS.md section 10 for continuity and power-up checks.
Hardware performance, enclosure fit and a fabrication release remain unverified.
