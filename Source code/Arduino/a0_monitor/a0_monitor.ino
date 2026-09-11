// A0, as numbers in the Serial Monitor.
//
// A diagnostic sketch, not part of the installation. It answers one
// question with the multimeter still in your other hand: is the wire from
// a body's JST really arriving on A0? `microphone_plotter` draws the
// signal's shape; this prints it, ten lines a second, so a DC loopback
// test reads as a number and a microphone reads as a number that moves.
//
// **It drives no pin**, for the plotter's reason: it is flashed onto the
// installation's own Mega, where every other pin belongs to firmware 4.
// No pinMode, and above all no INPUT_PULLUP - a pull-up on A0 reads 1023
// with nothing connected, which is exactly the answer the 5 V loopback
// test is looking for.
//
// What each reading means, jumper fitted across J11 1-2 (female1):
//
//   ~1023, swing ~0   the body's microphone wire is tied to 5 V at the
//                     far end - the loopback test passes
//   ~0, swing ~0      tied to GND at the far end
//   wandering, any    nothing is driving A0: jumper off, or a broken wire
//   ~256, swing grows the MAX9814 - biased at 1.25 V, and min and max
//     with sound      open apart when you talk or play music at it
//
// Volts are computed against 5.00 V, but the ADC's reference is the
// Mega's own 5 V, which on USB is anywhere from 4.7 to 5.1 V. Trust the
// counts; read the volts as approximate.
//
// Serial Monitor at 115200, not the installation's 1 Mbaud. When you are
// done, put firmware 4 back with `tests > manual tests > test microphone
// signal > flash colloquy firmware back`.

#define PIN A0
#define BAUDRATE 115200
#define LINE_MS 100

void setup() {
  Serial.begin(BAUDRATE);
  Serial.println();
  Serial.println("a0_monitor: last, min and max of A0 over each 100 ms");
}

void loop() {
  uint16_t lowest = 1023;
  uint16_t highest = 0;
  uint16_t last = 0;

  // Sample the whole window rather than once per line: one sample every
  // 100 ms of a microphone is a random point on a waveform, and only the
  // spread between min and max says whether sound is arriving.
  uint32_t started = millis();
  while (millis() - started < LINE_MS) {
    last = analogRead(PIN);
    if (last < lowest) lowest = last;
    if (last > highest) highest = last;
  }

  Serial.print("A0 ");
  Serial.print(last);
  Serial.print("  (");
  Serial.print(last * 5.0 / 1023.0, 2);
  Serial.print(" V)   min ");
  Serial.print(lowest);
  Serial.print("  max ");
  Serial.print(highest);
  Serial.print("  swing ");
  Serial.println(highest - lowest);
}
