# exposition
Colloquy of Mobiles for exposition in ZKM

## Hardware
- `CAD/KiCad/tj_brain`: **TJ Brain**, one Teensy 4.1 controller per unit (female 1-3, male 1-2, bar).
  It brings back T. J. McLeish's distributed 2018 architecture and has a DA-15 body connector
  compatible with the female harnesses.
- `CAD/KiCad/tj_backplane`: **TJ Backplane**, the 12V / 5V splitter (fused, with LEDs) that feeds the
  brains and the USB hub.
- `CAD/KiCad/electronic box`: the previous centralised board (Arduino Mega + U2D2).
- `Source code/Teensy/tj_brain_test`: Teensy pin map and bring-up test sketch for the TJ Brain.

## Todo
In KiCad:
- Choose the footprint for power supply capacitor.
- Check dimension of jack barrel.


## Todo