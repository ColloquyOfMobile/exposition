"""Which dynamixel id belongs to which body.

Mirrors U2D2._dxls (colloquy/hardware/u2d2/__init__.py): dxl_list[i]
carries dynamixel_id = i + 1, and the bodies sit at indices 0/2/4
(females), 6/7 (males), 8 (the bar), with the three mirrors in the gaps
between the females at 1/3/5. Kept in one place so the simulated sensor
geometry and the simulated-servo view can't drift apart, and so the
mapping is named rather than written as bare indices at each use.
"""

FEMALE_DXL_IDS = {"female1": 1, "female2": 3, "female3": 5}
MIRROR_DXL_IDS = {"mirror1": 2, "mirror2": 4, "mirror3": 6}
MALE_DXL_IDS = {"male1": 7, "male2": 8}
BAR_DXL_ID = 9

# What the simulated-servo view lists. The mirrors are left out on
# purpose: nothing drives them yet, so a row for each would be three
# lines of "still at zero" under the bodies that do move.
BODY_DXL_IDS = {**FEMALE_DXL_IDS, **MALE_DXL_IDS, "bar": BAR_DXL_ID}
