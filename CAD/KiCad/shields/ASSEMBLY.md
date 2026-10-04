# Assembly and variants

The default native voice layouts are female1 Thomas (1012Hz) and active 1414.
All five Thomas populations and all thirteen active populations use their own
complete BOM under `variants/`. A BOM changes population, never connector order.
Mark the fitted body or corner in the front white box and tick its row in the
back silkscreen table. The same artwork supports every population. The
population.json files describe assembly choices; no memory chip is fitted.

Build in this order: (1) backplane, five Thomas cards and MSGEQ7 analyser with
Mega/firmware 4; (2) Teensy adapter; (3) direct analyser; (4) active cards
1414, 4000, 8000, 250, 500 in body order. Other corners come later as needed.

Fit gold-plated contacts on both halves. Remove male pin 6/22 and block the
matching socket cavity. Sockets are on B.Cu; all small parts are on F.Cu.
Use insulated M3 standoffs. Do not hot-plug any card. Verify contact numbering
with a meter before fitting silicon. Direct analyser JSRC1 defaults to pins
1-2 (HARNESS); pins 2-3 select the bench JST. All attenuation bypasses are OPEN.

The 5V backplane rail, USB-derived MEGA_5V and IOREF are distinct supplies.
Follow REVIEW.md and SHIELDS.md section 10 for continuity and power-up checks.
Hardware performance, enclosure fit and a fabrication release remain unverified.
