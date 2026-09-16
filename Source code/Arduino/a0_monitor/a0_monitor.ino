// A0, as numbers in the Serial Monitor and as a trace in the Serial Plotter.
//
// A diagnostic sketch, not part of the installation. It answers one
// question with the multimeter still in your other hand: is the wire from
// a body's JST really arriving on A0? `microphone_plotter` draws the
// signal's shape at fifty windows a second; this one runs slow enough to
// read, so a DC loopback test reads as a number and a microphone reads as
// a number that moves - and the same line, unchanged, draws in the IDE's
// Serial Plotter (Tools > Serial Plotter, same port, same 115200).
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
// The volts column is gone, and the plotter is what took it. A line the
// plotter can draw is `name:value` pairs and nothing else, so a "(2.50
// V)" in the middle of it costs the whole trace; and the volts were
// approximate anyway - the ADC's reference is the Mega's own 5 V, which
// on USB is anywhere from 4.7 to 5.1 V, so the counts were always the
// thing to trust. The three landmarks: 1023 is about 5 V, 512 about
// 2.5 V, 256 about 1.25 V.
//
// Serial Monitor at 115200, not the installation's 1 Mbaud. When you are
// done, put firmware 4 back with `tests > manual tests > test microphone
// signal > flash colloquy firmware back`.

#define PIN A0
#define BAUDRATE 115200

// How long each line looks at, and so how fast lines arrive: ten a
// second. Deliberately slower than `microphone_plotter`'s 20 ms, because
// this sketch has to be readable as text while it is being drawn -
// fifty lines a second is a blur in the Monitor - and ten a second still
// fills the plotter's fifty-point window with five seconds of history,
// which is long enough to see a swing open and close as you talk.
#define LINE_MS 100

void setup() {
  Serial.begin(BAUDRATE);

  // Nothing is announced. A banner is a line the plotter cannot parse,
  // and the one it cannot parse is the first one it is given. The four
  // names below label the traces on their own.
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

  // `name:value` pairs, comma separated, one line - the Serial Plotter's
  // own format, and still a sentence in the Monitor. swing is drawn on
  // the same 0..1023 axis as the rest, where it lies flat on the bottom
  // and lifts off it the moment sound arrives: on a DC loopback test
  // that flat line is the pass, and on a microphone it is the signal.
  Serial.print("A0:");
  Serial.print(last);
  Serial.print(",min:");
  Serial.print(lowest);
  Serial.print(",max:");
  Serial.print(highest);
  Serial.print(",swing:");
  Serial.println(highest - lowest);
}
