// microphone_sampler.ino - a Mega that does nothing but sample a microphone.
//
// It captures a block of samples off one ADC pin as fast as the ADC will
// go, times the block so the sample rate is measured rather than assumed,
// and sends the samples on. That is the whole sketch. Every judgement
// about what is in them - which frequency, how loud, whether it is there
// at all - is made on the PC by `colloquy/tests/test_goertzel_ear/`.
//
// WHY THE ARITHMETIC IS NOT HERE
// ------------------------------
// It used to be: `Source code/Arduino/goertzel_ear/` is one board that
// makes a tone *and* runs a Goertzel bin over its own samples, and it is
// still there because it answers a different question - whether an AVR
// can do the listening in software, which is `one board per body`
// section 4.
//
// This one answers the question you actually have at a desk: **does this
// microphone hear this tone?** For that, the board being clever buys
// nothing and costs a great deal. Move the arithmetic to the PC and:
//
//   - the tone comes out of the PC's own sound card, so it can be a
//     clean sine at any frequency instead of a square wave from a timer
//     on a fixed pin, and there is no amplifier and no second speaker to
//     wire up or to blame;
//   - one capture is measured at all five pitches at once, because a
//     Goertzel is one pass per frequency over samples already in hand,
//     and the samples are in hand on a machine with memory to spare;
//   - the thresholds, the window and the bins are changed by editing
//     Python and pressing a link, not by reflashing;
//   - and what the board is doing is small enough to be obviously right.
//     A sampler that only samples cannot be wrong about a frequency.
//
// The cost is the wire: a block has to cross it. That is what the
// baud rate below is for.
//
// WIRING - two connections
// ------------------------
//   A0  <- microphone module out (a MAX9814's AOUT, or any line sitting
//          near mid-rail)
//   A1  <- a second microphone's out, for the `d` command. Leave it off
//          and `b` is unaffected; a pin with nothing on it does not read
//          silence, it wanders, so an empty A1 is visibly empty rather
//          than quietly flat.
//   GND <- common with both microphone modules
// Nothing else. The tone is in the room, out of the computer's speakers,
// and does not touch this board at all. See HARDWARE_SETUP.md, section 8.
//
// SERIAL, 1 Mbaud, one command a line
// -----------------------------------
//   b   capture a block off A0 and send it
//   d   capture A0 and A1 together and send both
//   ?   what it is set to, and the sample rate it last measured
//
// TWO COMMANDS, AND WHY `b` DID NOT GROW A SECOND CHANNEL
// ------------------------------------------------------
// `b` is what `test_goertzel_ear` asks for, and what comes back it runs
// five Goertzel bins over. Interleaving a second channel into that reply
// would leave every one of those bins computed over two microphones'
// samples alternating - which does not fail, it just answers wrongly, and
// the frequency it would answer about is not one anybody played. So the
// single-channel reply is untouched to the last byte and the second
// channel is a second command, used by `tests > manual tests > scope`.
// Replies are one line beginning with a keyword, so a driver can parse
// them without knowing the prose.
//
// 1 Mbaud is not a flourish. A block is 512 numbers - about 2 kB of
// text - and at 115200 that alone is 180 ms, which would make a live
// reading crawl. At 1 Mbaud it is about 20 ms, and 1 Mbaud is the rate
// the installation's own sketch already runs at on the same kind of
// board, so it is a proven rate here rather than an optimistic one.

#define FIRMWARE_VERSION 2

#define MIC_PIN A0       // any ADC pin; A0 to match the installation
#define MIC_PIN_B A1     // the second channel, for `d` only
#define BAUDRATE 1000000

// 512 samples at ~19.2 kSPS is a 27 ms window and a bin about 37 Hz
// wide. The closest two pitches this piece uses are 160 Hz apart, so
// that separates them with room over. A power of two only because it
// makes the bin arithmetic tidy; nothing here needs an FFT.
#define SAMPLES 512

// ADC prescaler 64 -> a 250 kHz ADC clock -> ~19.2 kSPS. Above the
// datasheet's 200 kHz for a full ten bits, so call it eight or nine - it
// is a level comparison, not a measurement of absolute amplitude.
// Nyquist for the highest pitch this piece uses (6250 Hz) is 12.5 kSPS,
// so there is room.
#define ADC_PRESCALER 6  // 2^6 = 64

int16_t samples[SAMPLES];
float sampleRate = 0.0;

// `d` fills the same buffer with interleaved pairs rather than taking a
// second one. It is the same 512 conversions either way, so the window is
// the same 27 ms, the reply is the same size, and the Mega's RAM sees no
// difference at all - what is halved is how many of them each channel
// gets. Per channel that is about 9.6 kSPS, so the pair rate below is
// what goes out as `fs=`, because a rate that is not per channel is not
// a rate anybody downstream can use.
#define PAIRS (SAMPLES / 2)
float pairRate = 0.0;

// ------------------------------------------------------------ sampling

void adcSelect(uint8_t pin) {
  ADMUX = _BV(REFS0) | (pin - A0);             // AVcc reference
}

uint16_t adcRead() {
  ADCSRA |= _BV(ADSC);
  while (ADCSRA & _BV(ADSC)) {}
  return ADC;
}

void adcBegin() {
  adcSelect(MIC_PIN);
  ADCSRB = 0;
  ADCSRA = _BV(ADEN) | ADC_PRESCALER;
  adcRead();                                   // one throwaway conversion
}

// Fill the buffer as fast as the ADC will go, and time the block so the
// rate is known rather than assumed. Everything downstream is computed
// from this number, so a different board or prescaler needs no edit
// anywhere else - not here, and not in Python.
//
// Nothing is sent while this runs. Sampling and sending are separated on
// purpose: a UART write that blocked mid-block would stretch the window
// unevenly and put a step in the middle of the very signal being
// measured.
void capture() {
  adcSelect(MIC_PIN);
  unsigned long began = micros();
  for (int i = 0; i < SAMPLES; i++) {
    samples[i] = (int16_t)adcRead();
  }
  unsigned long took = micros() - began;
  sampleRate = (float)SAMPLES * 1000000.0 / (float)took;
}

// Both channels, alternating, into the one buffer as interleaved pairs.
//
// The two halves of a pair are one conversion apart - about 52 us here -
// not simultaneous. There is one converter behind a multiplexer and no
// sample-and-hold per channel, so simultaneous is not on offer at any
// price, and 52 us is a third of a cycle at 6 kHz. It costs nothing for
// what this is for (is this microphone producing anything, and how does
// it compare with that one) and it would matter for anything measuring
// phase between the two, which nothing here does.
//
// No throwaway conversion after the mux changes. The channel is selected
// combinationally and the sample is taken in the first cycles of the
// conversion that follows, so the reading is of the pin just selected -
// what a throwaway protects against is a *high impedance* source not
// having charged the sample capacitor, and a MAX9814's output is a long
// way from that. On a high impedance source, expect each channel to be
// dragged towards the other's level.
void captureDual() {
  unsigned long began = micros();
  for (int i = 0; i < PAIRS; i++) {
    adcSelect(MIC_PIN);
    samples[2 * i] = (int16_t)adcRead();
    adcSelect(MIC_PIN_B);
    samples[2 * i + 1] = (int16_t)adcRead();
  }
  unsigned long took = micros() - began;
  pairRate = (float)PAIRS * 1000000.0 / (float)took;
}

// -------------------------------------------------------------- output

// One line: a keyword, the name=value pairs a reader needs to make sense
// of what follows, then the samples themselves separated by spaces. Text
// rather than binary so that the Serial Monitor is still a usable second
// opinion on what this board is sending.
void sendBlock() {
  Serial.print("block n=");
  Serial.print(SAMPLES);
  Serial.print(" fs=");
  Serial.print(sampleRate, 1);
  for (int i = 0; i < SAMPLES; i++) {
    Serial.print(' ');
    Serial.print(samples[i]);
  }
  Serial.println();
}

// The pairs, as one line: a keyword of its own so that nothing reading
// for `block ` can ever be handed two interleaved microphones, then `n=`
// pairs and `fs=` per channel, then a0 a1 a0 a1 ...
void sendDualBlock() {
  Serial.print("pair n=");
  Serial.print(PAIRS);
  Serial.print(" fs=");
  Serial.print(pairRate, 1);
  Serial.print(" pins=A");
  Serial.print(MIC_PIN - A0);
  Serial.print(",A");
  Serial.print(MIC_PIN_B - A0);
  for (int i = 0; i < SAMPLES; i++) {
    Serial.print(' ');
    Serial.print(samples[i]);
  }
  Serial.println();
}

void status() {
  Serial.print("status firmware=");
  Serial.print(FIRMWARE_VERSION);
  Serial.print(" mic_pin=A");
  Serial.print(MIC_PIN - A0);
  Serial.print(" n=");
  Serial.print(SAMPLES);
  Serial.print(" fs=");
  Serial.print(sampleRate, 1);
  Serial.print(" pin_b=A");
  Serial.print(MIC_PIN_B - A0);
  Serial.print(" pairs=");
  Serial.print(PAIRS);
  Serial.println();
}

// ------------------------------------------------------------- command

void runCommand(char *line) {
  switch (line[0]) {
    case 'b':
      capture();
      sendBlock();
      break;
    case 'd':
      captureDual();
      sendDualBlock();
      break;
    case '?':
      status();
      break;
    default:
      Serial.println("error commands: b | d | ?");
      break;
  }
}

void setup() {
  pinMode(MIC_PIN, INPUT);

  Serial.begin(BAUDRATE);
  adcBegin();
  capture();                        // so the greeting knows the rate

  Serial.print("microphone_sampler firmware=");
  Serial.print(FIRMWARE_VERSION);
  Serial.print(" mic_pin=A");
  Serial.print(MIC_PIN - A0);
  Serial.print(" n=");
  Serial.print(SAMPLES);
  Serial.print(" fs=");
  Serial.print(sampleRate, 1);
  Serial.print(" baud=");
  Serial.print(BAUDRATE);
  Serial.println();
}

void loop() {
  static char line[16];
  static byte length = 0;

  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (length) {
        line[length] = 0;
        runCommand(line);
        length = 0;
      }
    } else if (length < sizeof(line) - 1) {
      line[length++] = c;
    }
  }
}
