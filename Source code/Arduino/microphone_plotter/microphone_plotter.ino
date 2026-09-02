// One microphone, straight onto a plot.
//
// This is a diagnostic sketch, not part of the installation. It is here
// because the sound chain has nine links in it and only one of them can
// be looked at with your own eyes: the MAX9814's output, before the
// MSGEQ7 gets hold of it. Everything downstream of that point is already
// covered - `test audio bringup` takes the chain apart by arranging for
// the faults to have different shapes, and `test audio loop` grades the
// whole twenty-five-verdict grid. Neither can tell you whether a
// microphone is producing a signal at all, because both of them are
// reading the analyser and the analyser is the next link along.
//
// So this sketch does exactly one thing: read one ADC pin as fast as the
// converter honestly goes, and print numbers the Arduino IDE's Serial
// Plotter can draw. Play music into a body from a phone, watch the trace.
// Sound arriving is a shape you recognise in a second and no reading of
// seven band values will ever be as convincing.
//
// **It drives no pin, and that is deliberate.** It is meant to be
// flashable onto the installation's own Mega as a last resort, where
// every NeoPixel line, all five tone pins and the analyser's strobe and
// reset belong to another sketch entirely. Leaving them as inputs means
// nothing lights, nothing sounds and nothing is driven into a board
// wired for firmware 4. Do not add a pinMode(OUTPUT) here.
//
// How to wire it, what the four traces mean and what each failure looks
// like are in the manual test that owns it, on the page under
// `tests > manual tests > test microphone signal > plotter setup`
// (Source code/Python/colloquy/tests/test_microphone_signal/
// MICROPHONE_PLOTTER.md). Read that first - one of the two ways of
// wiring this involves pulling something off J11, and there is a right
// order to do it in.

// Which pin the microphone's AOUT is on.
//
// A0 suits the recommended route, which is a spare Arduino used as a
// probe: its own A0 clipped to the microphone wire, its own GND clipped
// to the board's, and nothing about the installation touched. On the
// installation's own Mega there is no free ADC pin at all - A0..A4 are
// the five analyser outputs and A5..A15 are the photosensors - so that
// route borrows a female's photosensor pin and this becomes A5, A6 or
// A7. The document says which and in what order.
#define MIC_PIN A0

// ENVELOPE draws the signal's outline: the loudest and quietest sample
// in each short window, and the average. It is the mode for music, and
// the mode for "is anything arriving at all" - a voice or a beat paints
// a shape you recognise immediately.
//
// WAVE draws the samples themselves, in bursts, so a steady tone can be
// looked at as a waveform. Use it to tell a real 1 kHz tone from mains
// hum or from switching noise off a NeoPixel line, which look alike in
// envelope and nothing like each other here.
#define ENVELOPE 1
#define WAVE 2
#define MODE ENVELOPE

// Not the installation's 1 Mbaud. This sketch is read by the IDE's
// plotter rather than by the driver, and 115200 is the rate every
// version of that plotter offers without being asked twice. If the
// window fills with rubbish, this number and the one in the plotter's
// corner disagree - it is always that.
#define PLOT_BAUDRATE 115200

// How long each envelope point looks at. 20 ms is about a fiftieth of a
// second: fast enough that a drum beat is a spike rather than a smear,
// slow enough that a 160 Hz tone has three whole cycles inside it and so
// cannot be missed between two windows.
#define WINDOW_MS 20

// One burst of raw samples in WAVE mode. 400 at roughly 33 kSPS is 12 ms
// of sound - two cycles of the lowest voice, seventy-five of the
// highest - and 800 bytes of RAM, which even an Uno used as a probe has
// to spare.
#define WAVE_SAMPLES 400

// Where the MAX9814 sits when it is hearing nothing: its output is
// biased at 1.25 V, and 1.25 V of a 5 V reference read to ten bits is
// 256. Printed as a flat fourth trace on purpose - it is the line the
// other three should be arranged around, and a plot whose middle is
// anywhere else is answering the question before you have played
// anything.
#define BIAS_1V25 256

#if MODE == WAVE
// Only in the mode that uses it. 800 bytes is nothing on a Mega and
// half of an Uno's whole memory - measured, not guessed - and an Uno
// is exactly what somebody reaches for to use as a probe.
uint16_t burst[WAVE_SAMPLES];
#endif

void setup() {
  Serial.begin(PLOT_BAUDRATE);

  // The ADC's own clock, which the Arduino core leaves at 125 kHz - one
  // conversion every 112 us, so 8.9 kSPS. That is under two samples per
  // cycle of the 6.25 kHz voice: the tone would alias down into
  // something slower and entirely fictional, and a plot of a fiction is
  // worse than no plot. Prescaler 32 gives a 500 kHz ADC clock and about
  // 33 kSPS, which is comfortably above everything in this piece.
  //
  // The datasheet's 200 kHz ceiling is for the full ten bits of
  // accuracy. Nothing here is a measurement to the last bit - the
  // question is whether a shape is there - so the trade is the right way
  // round.
  ADCSRA = (ADCSRA & 0xF8) | 0x05;

  // Read only. No pinMode, and above all no INPUT_PULLUP: a pull-up on
  // this pin would drag the microphone's output towards 5 V and the
  // trace would be a flat line near 1023 that looks exactly like a
  // hardware fault.
}

void loop() {
#if MODE == ENVELOPE
  plotEnvelope();
#else
  plotWave();
#endif
}

// One window's outline: the extremes and the middle.
//
// min and max are what you watch. Sound is the two of them opening away
// from each other and closing again with the music; silence is the two of
// them squeezed onto the bias line. mean is the slow one - it should sit
// on BIAS_1V25 and stay there, and a mean that wanders is a coupling or
// supply fault rather than anything to do with what is in the room.
#if MODE == ENVELOPE
void plotEnvelope() {
  uint16_t lowest = 1023;
  uint16_t highest = 0;
  uint32_t total = 0;
  uint32_t taken = 0;

  uint32_t started = millis();
  while (millis() - started < WINDOW_MS) {
    uint16_t value = analogRead(MIC_PIN);
    if (value < lowest) lowest = value;
    if (value > highest) highest = value;
    total += value;
    taken++;
  }

  Serial.print("min:");
  Serial.print(lowest);
  Serial.print(",max:");
  Serial.print(highest);
  Serial.print(",mean:");
  Serial.print((uint16_t)(total / taken));
  Serial.print(",bias1v25:");
  Serial.println(BIAS_1V25);
}
#endif

// A burst of raw samples, captured at full rate and printed afterwards.
//
// Captured first and printed second because printing is far slower than
// sampling: 400 numbers take about a fifth of a second to leave the port
// and 12 ms to collect. Sampling while printing would space the samples
// unevenly and draw a waveform that is not the one in the wire.
#if MODE == WAVE
void plotWave() {
  for (uint16_t index = 0; index < WAVE_SAMPLES; index++) {
    burst[index] = analogRead(MIC_PIN);
  }

  for (uint16_t index = 0; index < WAVE_SAMPLES; index++) {
    Serial.print("sample:");
    Serial.print(burst[index]);
    Serial.print(",bias1v25:");
    Serial.println(BIAS_1V25);
  }
}
#endif
