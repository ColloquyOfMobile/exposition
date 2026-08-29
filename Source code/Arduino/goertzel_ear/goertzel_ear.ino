// goertzel_ear.ino - one board that makes a tone and says whether it hears it.
//
// For an Arduino Mega 2560. A bench instrument, not part of the
// installation: it answers the one question the installation's own
// hearing side cannot yet be trusted on - *is a tone of this frequency
// actually arriving at this microphone?* - with a number rather than an
// opinion.
//
// It does both halves itself on purpose. A speaker and a microphone on
// one board means the loop can be closed on a desk with nothing else
// plugged in, and a failure is either the air between them or the board,
// with no cable in between to blame.
//
// WHY GOERTZEL AND NOT AN MSGEQ7
// ------------------------------
// The MSGEQ7 answers with seven fixed, octave-wide bands, and the five
// pitches this piece uses were *chosen* to land one per band - two of
// them still in adjacent bands with the skirts overlapping. Goertzel
// answers about one frequency, in a bin as narrow as the capture is long,
// so it rejects the room far better and needs no analyser chip, no
// commoned strobe and no support network. One multiply-accumulate per
// sample per frequency.
//
// HOW IT RUNS
// -----------
// Sampling and arithmetic are deliberately separated. A block of samples
// is captured at full ADC speed into RAM, and only then is the Goertzel
// run over the block. That way the maths cannot slow the sampling down,
// the sample rate is whatever the ADC gives and is *measured* rather than
// assumed, and several frequencies come out of one capture for free.
//
// The tone is a hardware timer toggling its own pin in CTC mode - no
// interrupts at all - so generating it cannot disturb the sampling. That
// is the same reason the installation's own sketch uses timers rather
// than tone().
//
// WIRING
// ------
//   D11 (OC1A) -> amplifier in (through a divider if the amp wants one)
//   A0         <- microphone module out (MAX9814 AOUT, or any biased
//                 line sitting near mid-rail)
//   GND        <- common with both
// See HARDWARE_SETUP.md, "Hearing a tone without an MSGEQ7".
//
// SERIAL, 115200, one command a line
// ---------------------------------
//   f <hz>   set the frequency to make and to listen for
//   t 0|1    tone off / on
//   m        measure once, print one reading
//   s        self test: floor with the tone off, level with it on, verdict
//   w        sweep the installation's five pitches, self-testing each
//   ?        what it is set to, and the measured sample rate
// Every reply is one line beginning with a keyword, so a driver can parse
// it without knowing the prose.

#define FIRMWARE_VERSION 1

#define TONE_PIN 11      // OC1A on a Mega 2560. Fixed by silicon.
#define MIC_PIN A0       // any ADC pin; A0 to match the installation
#define BAUDRATE 115200

// 512 samples at ~19.2 kSPS is a 27 ms window and a bin about 37 Hz wide.
// A power of two only because it makes the bin arithmetic tidy; nothing
// here needs an FFT.
#define SAMPLES 512

// ADC prescaler 64 -> a 250 kHz ADC clock -> ~19.2 kSPS. Above the
// datasheet's 200 kHz for a full ten bits, so call it eight or nine - it
// is a level comparison, not a measurement of absolute amplitude. Nyquist
// for the highest pitch this piece uses (6250 Hz) is 12.5 kSPS, so there
// is room.
#define ADC_PRESCALER 6  // 2^6 = 64

// A tone counts as heard when its bin rises this much over the same bin
// measured in silence. Blunt on purpose, and the same spirit as the
// installation's own MARGIN: it rejects drift and room noise and measures
// nothing.
#define HEARD_MARGIN 4.0

// The five the installation uses, for the sweep.
const long SWEEP_HZ[] = {160, 400, 1000, 2500, 6250};
const int SWEEP_COUNT = sizeof(SWEEP_HZ) / sizeof(SWEEP_HZ[0]);

int16_t samples[SAMPLES];
long toneHz = 1000;
bool toneOn = false;
float sampleRate = 0.0;

// ---------------------------------------------------------------- tone

// CTC on Timer1, toggling OC1A. f = 16e6 / (2 * 8 * (OCR1A + 1)) with the
// prescaler at 8, so OCR1A = 1e6/f - 1: 6249 for 160 Hz, 159 for 6250.
// Both fit a 16-bit compare, which is why this is Timer1 and not one of
// the 8-bit ones.
void toneStart(long hz) {
  if (hz < 16 || hz > 200000) return;
  long ocr = (1000000L / hz) - 1;
  noInterrupts();
  TCCR1A = _BV(COM1A0);              // toggle OC1A on compare match
  TCCR1B = _BV(WGM12) | _BV(CS11);   // CTC, prescaler 8
  OCR1A = (uint16_t)ocr;
  TCNT1 = 0;
  interrupts();
  toneOn = true;
}

void toneStop() {
  TCCR1A = 0;
  TCCR1B = 0;
  digitalWrite(TONE_PIN, LOW);
  toneOn = false;
}

// ------------------------------------------------------------ sampling

void adcBegin() {
  ADMUX = _BV(REFS0) | (MIC_PIN - A0);        // AVcc reference
  ADCSRB = 0;
  ADCSRA = _BV(ADEN) | ADC_PRESCALER;
  ADCSRA |= _BV(ADSC);                         // one throwaway conversion
  while (ADCSRA & _BV(ADSC)) {}
}

// Fill the buffer as fast as the ADC will go, and time the block so the
// rate is known rather than assumed. Everything downstream uses this
// number, so a different board or prescaler needs no edit anywhere else.
void capture() {
  unsigned long began = micros();
  for (int i = 0; i < SAMPLES; i++) {
    ADCSRA |= _BV(ADSC);
    while (ADCSRA & _BV(ADSC)) {}
    samples[i] = (int16_t)ADC;
  }
  unsigned long took = micros() - began;
  sampleRate = (float)SAMPLES * 1000000.0 / (float)took;
}

// ------------------------------------------------------------ goertzel

// The magnitude of one frequency in the captured block, per sample.
//
// `k` is rounded to a whole number of cycles in the window so the bin
// sits exactly on a basis frequency and nothing is lost to scalloping;
// the frequency actually measured is therefore k*fs/N, which report()
// prints rather than hiding.
float goertzel(long hz) {
  if (sampleRate <= 0) return 0;

  int k = (int)(0.5 + ((float)SAMPLES * (float)hz) / sampleRate);
  if (k < 1) k = 1;
  if (k > SAMPLES / 2 - 1) k = SAMPLES / 2 - 1;

  float omega = 2.0 * PI * (float)k / (float)SAMPLES;
  float coeff = 2.0 * cos(omega);

  // The microphone sits at mid-rail, so the block's own mean is the DC to
  // take out. Doing it here rather than with a capacitor keeps the input
  // network to a wire.
  long total = 0;
  for (int i = 0; i < SAMPLES; i++) total += samples[i];
  float mean = (float)total / (float)SAMPLES;

  float s1 = 0, s2 = 0;
  for (int i = 0; i < SAMPLES; i++) {
    float s = ((float)samples[i] - mean) + coeff * s1 - s2;
    s2 = s1;
    s1 = s;
  }
  float power = s1 * s1 + s2 * s2 - coeff * s1 * s2;
  if (power < 0) power = 0;
  return sqrt(power) / (float)SAMPLES;
}

float binHz(long hz) {
  int k = (int)(0.5 + ((float)SAMPLES * (float)hz) / sampleRate);
  return (float)k * sampleRate / (float)SAMPLES;
}

// -------------------------------------------------------------- output

void report(const char *what, long hz, float level) {
  Serial.print(what);
  Serial.print(" hz=");
  Serial.print(hz);
  Serial.print(" bin=");
  Serial.print(binHz(hz), 1);
  Serial.print(" level=");
  Serial.print(level, 2);
  Serial.print(" fs=");
  Serial.print(sampleRate, 0);
  Serial.println();
}

// One measurement of one frequency, tone left as it was.
float measure(long hz) {
  capture();
  return goertzel(hz);
}

// Floor with the tone off, level with it on, and the difference. The
// difference is the only number worth believing: a MAX9814's AGC makes
// the absolute level meaningless on its own.
void selfTest(long hz) {
  bool was = toneOn;

  toneStop();
  delay(60);                       // let the AGC and the room settle
  float floorLevel = measure(hz);

  toneStart(hz);
  delay(120);
  float toneLevel = measure(hz);

  if (!was) toneStop();

  float rise = toneLevel - floorLevel;
  Serial.print("test hz=");
  Serial.print(hz);
  Serial.print(" bin=");
  Serial.print(binHz(hz), 1);
  Serial.print(" floor=");
  Serial.print(floorLevel, 2);
  Serial.print(" tone=");
  Serial.print(toneLevel, 2);
  Serial.print(" rise=");
  Serial.print(rise, 2);
  Serial.print(" heard=");
  Serial.print(rise >= HEARD_MARGIN ? 1 : 0);
  Serial.print(" fs=");
  Serial.print(sampleRate, 0);
  Serial.println();
}

void status() {
  Serial.print("status firmware=");
  Serial.print(FIRMWARE_VERSION);
  Serial.print(" hz=");
  Serial.print(toneHz);
  Serial.print(" tone=");
  Serial.print(toneOn ? 1 : 0);
  Serial.print(" samples=");
  Serial.print(SAMPLES);
  Serial.print(" fs=");
  Serial.print(sampleRate, 0);
  Serial.print(" margin=");
  Serial.print(HEARD_MARGIN, 1);
  Serial.println();
}

// ------------------------------------------------------------- command

void runCommand(char *line) {
  char verb = line[0];
  long value = atol(line + 1);

  switch (verb) {
    case 'f':
      if (value >= 16 && value <= 20000) {
        toneHz = value;
        if (toneOn) toneStart(toneHz);
        Serial.print("ok hz=");
        Serial.println(toneHz);
      } else {
        Serial.println("error hz out of range 16..20000");
      }
      break;
    case 't':
      if (value) toneStart(toneHz); else toneStop();
      Serial.print("ok tone=");
      Serial.println(toneOn ? 1 : 0);
      break;
    case 'm':
      report("reading", toneHz, measure(toneHz));
      break;
    case 's':
      selfTest(toneHz);
      break;
    case 'w':
      for (int i = 0; i < SWEEP_COUNT; i++) selfTest(SWEEP_HZ[i]);
      Serial.println("sweep done");
      break;
    case '?':
      status();
      break;
    default:
      Serial.println("error commands: f <hz> | t 0|1 | m | s | w | ?");
      break;
  }
}

void setup() {
  pinMode(TONE_PIN, OUTPUT);
  digitalWrite(TONE_PIN, LOW);
  pinMode(MIC_PIN, INPUT);

  Serial.begin(BAUDRATE);
  adcBegin();
  capture();                        // so the first status knows the rate

  Serial.print("goertzel_ear firmware=");
  Serial.print(FIRMWARE_VERSION);
  Serial.print(" tone_pin=");
  Serial.print(TONE_PIN);
  Serial.print(" mic_pin=A");
  Serial.print(MIC_PIN - A0);
  Serial.print(" fs=");
  Serial.println(sampleRate, 0);
  status();
}

void loop() {
  static char line[24];
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
