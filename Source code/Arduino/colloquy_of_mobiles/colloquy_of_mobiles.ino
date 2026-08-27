#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>

// ##########################################################
// The link, and what the driver on the other end has to agree with.
//
// Both numbers below are read straight out of this file by the Python
// side (colloquy/hardware/arduino/firmware.py), the same way it already
// reads the paths further down, so this is the one place either of them
// is written. They are also sent on the wire in the greeting, so a board
// running something else says so rather than being mistaken for this one.

// Bumped whenever the serial protocol changes in a way that would make an
// older driver misread this board: a renamed path, a reply of a different
// shape. Nothing about such a mismatch is loud on its own - an unknown
// path is answered with an empty line - so the only symptom is a female
// who never sees a pattern, which is why the driver refuses a version it
// was not written for.
//
// 1: the original. Greeted with a bare "Hello!" and ran at 57600.
// 2: greets with JSON saying this version and this baud rate, answers
//    "version" with the same, and runs the link at 1 Mbaud.
// 3: the audio subsystem. Five tones on five hardware timers and five
//    MSGEQ7 analyser modules read through one commoned strobe - see the
//    PINs block below. Four NeoPixel lines moved to make room for them,
//    so a board flashed with 2 and wired for 3 lights the wrong strips:
//    this is exactly the kind of mismatch the version number is for.
// 4: the males took the two low voices and the females the three high
//    ones. Nothing about the board changed - the pitches stayed on their
//    timers and the bodies moved across the pins - but a driver judging
//    a firmware-3 board by this table gets every verdict wrong while
//    everything still appears to work: a tone comes out, a band rises,
//    and only the attribution is silently for another body. That is the
//    worst kind of mismatch and the reason this is a version and not a
//    quiet edit.
#define FIRMWARE_VERSION 4

// As fast as this link will honestly go. The Mega's USART divides its
// 16 MHz exactly at 1 Mbaud (U2X, UBRR = 1), so there is no framing error
// to accumulate, and the 16U2 bridge carries it. 2 Mbaud divides exactly
// too, and is also the rate at which this pair is known to start dropping
// bytes - and a dropped byte here is a light sensor reading that never
// comes back.
//
// It was 57600 until the pattern reading needed the samples: a female
// decodes her sensor by binning readings against a wall clock, and at
// 57600 one round trip cost about 12ms of a 200ms bit. See
// colloquy/light_pattern_timing.py for where the 200ms comes from.
#define SERIAL_BAUDRATE 1000000UL

// One command line, with room to spare: the longest this sketch is sent
// is a four-channel pixel fill, about seventy characters. It is read into
// a fixed buffer rather than a String - see loop().
#define COMMAND_BUFFER_SIZE 128

// ##########################################################
// PINs
//
// Four of the NeoPixel lines moved on 2026-08-26, and the reason is worth
// knowing before moving any of them again: a NeoPixel line is bit-banged
// and can be *any* pin, while a tone output cannot be. Each of the five
// tone pins below is the OCnA output of one hardware timer and is fixed
// in the silicon. So when the two wanted the same pins, the lights moved
// and the tones did not.
//
// This expects the board to have been reworked to match. The cuts and
// jumpers are written down in colloquy/hardware/electronics/, which is
// also on the page under `hardware`.

// --- lights -----------------------------------------------------------
#define FEMALE1_NEOPIXEL_PIN 14  // was D6, which is now the 1 kHz tone
#define FEMALE2_NEOPIXEL_PIN 7
#define FEMALE3_NEOPIXEL_PIN 8

#define FEMALE_NUM_PIXELS 50  // Female LED number

#define MALE1_BODY_NEOPIXEL_PIN 9
#define MALE2_BODY_NEOPIXEL_PIN 15  // was D10, which is now the 6.25 kHz tone

// These two carry the PCB nets named beside them, and the board and this
// sketch have disagreed about which male owns which since long before the
// audio rework: the schematic calls D4 "male2/bar neopixel" and D5
// "male1/bar neopixel", while the strips were constructed on those pins
// the other way round. The rework kept each strip on the wire it was
// actually driving, so nothing in the room changed. If the up-rings come
// out on the wrong male, these two are the swap - and then the net names
// are the ones that were right.
#define MALE1_UP_RING_NEOPIXEL_PIN 17  // PCB net "male2/bar neopixel", was D4
#define MALE2_UP_RING_NEOPIXEL_PIN 16  // PCB net "male1/bar neopixel", was D5

#define NUMBER_OF_PIXEL_IN_MALE_BODY 40

// --- voices -----------------------------------------------------------
// One tone per body, five bodies, five hardware timers. The frequencies,
// the pins and the OCR values are Thomas Erforth's, out of
// `Source code/Thomas/AudioAnalyzer.h`; his own tester firmware makes the
// same five tones on the same five pins, which is what makes his bench
// results transferable to this board.
//
// Each tone sits in a different one of the analyser's seven bands, and
// that is the whole design: five bodies, five voices, no two competing
// for one band. 63 Hz and 16 kHz are left unused - a typical electret
// microphone is only specified from 100 Hz to 10 kHz.
//
// The pins are NOT a free choice. Timer n toggles its own OCnA pin and no
// other, so moving a tone means moving a body's whole audio channel on
// the board.
//
// The males have the two low voices and the females the three high ones.
// A pitch cannot be moved to another body on its own: the pitch belongs
// to the timer, Thomas's OCR values are indexed by timer, and 6250 Hz is
// on timer 2 precisely because timer 2 is the 8-bit one - at prescaler 8
// it cannot reach down to 160 Hz at all. So the pitches stayed where they
// were and the bodies moved across the pins. Every OCR value and every
// filter channel is untouched; what changed is which body each one is.
#define MALE1_TONE_PIN 11    // OC1A - timer 1 -  160 Hz
#define MALE2_TONE_PIN 5     // OC3A - timer 3 -  400 Hz
#define FEMALE1_TONE_PIN 6   // OC4A - timer 4 - 1000 Hz
#define FEMALE2_TONE_PIN 46  // OC5A - timer 5 - 2500 Hz
#define FEMALE3_TONE_PIN 10  // OC2A - timer 2 - 6250 Hz

// --- ears -------------------------------------------------------------
// Five MSGEQ7 modules on one carrier, one per body. Their STROBE and
// RESET are tied together across the back of the board, so one cycle
// through the seven bands reads all five bodies at once - which is why
// reading one body costs exactly what reading all five does.
#define ANALYSER_STROBE_PIN 4
#define ANALYSER_RESET_PIN 3

// Module 0 is on A0 and they ascend from there, in body order:
// female1, female2, female3, male1, male2. That is not a convention this
// sketch chose - the board already had female1..male2's microphone pairs
// on A0..A4, and the analyser modules took their place.
#define ANALYSER_FIRST_ADC A0
#define ANALYSER_MODULES 5
#define ANALYSER_BANDS 7

// ##########################################################
// Class definitions

class LightSensor{
public:
  const int pin;
  LightSensor(int pin) : pin(pin) {}
  String read(){
    int value = analogRead(pin);
    return String(value);
  }

};

// One body's voice: a square wave of one fixed pitch, on or off.
//
// The tone is made by the timer itself, not by this code and not by an
// interrupt: the timer runs in CTC mode and the compare-match output
// toggles its own pin in hardware. Two things follow, and both matter
// here.
//
// The first is that a tone costs nothing while it sounds. There is no
// ISR, so nothing competes with the serial link, and - the reason this is
// not `tone()` - nothing is disturbed by Adafruit_NeoPixel::show(), which
// turns interrupts off for a couple of milliseconds every time a pixel
// group is written. TJ's firmware had to mute the amplifier around every
// pixel write for exactly that reason (act_blockSound / act_unblockSound,
// CODE_DOCUMENTATION 9.13). This port writes pixels far more often than
// his did, and does not have to.
//
// The second is that five simultaneous tones need five timers, one each,
// which is why there is a fixed pin per body rather than a pitch that can
// be asked for. Timer 0 is not among them: it is the one the Arduino core
// runs millis(), micros() and delay() on, and the analyser read below
// depends on those.
class Voice {
public:
  const uint8_t pin;
  const uint8_t timer;  // 1..5, the AVR timer this voice is made on
  const uint16_t hz;
  const uint16_t ocr;

  Voice(uint8_t pin, uint8_t timer, uint16_t hz, uint16_t ocr)
    : pin(pin), timer(timer), hz(hz), ocr(ocr) {}

  void begin() {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
    silence();
  }

  bool isSinging() const {
    return _isSinging;
  }

  // {"path": "f1/speaker", "on": 1}. Answers with the state it is now in,
  // so a caller can read back what it asked for rather than assume it.
  String set(JsonDocument& doc) {
    int on = doc["on"] | 0;
    if (on) {
      sing();
    } else {
      silence();
    }
    return String(_isSinging ? 1 : 0);
  }

  void sing() {
    // COM1A0 / COM3A0 / COM4A0 / COM5A0 are all bit 6, and WGM12 / WGM32
    // / WGM42 / WGM52 are all bit 3, so one pair of literals covers all
    // four 16-bit timers. Timer 2 is the 8-bit one and its bits sit
    // elsewhere, which is the whole reason for the branch.
    if (timer == 2) {
      TCCR2A = (1 << COM2A0) | (1 << WGM21);  // toggle OC2A on match, CTC
      TCCR2B = 2;                             // prescaler 8
      OCR2A = (uint8_t)ocr;
    } else {
      *timerControlA() = (1 << COM1A0);              // toggle OCnA on match
      *timerControlB() = (1 << WGM12) | 1;           // CTC, prescaler 1
      *timerCompare() = ocr;
    }
    _isSinging = true;
  }

  void silence() {
    if (timer == 2) {
      TCCR2A = 0;
      TCCR2B = 0;
    } else {
      *timerControlA() = 0;
      *timerControlB() = 0;
    }
    // Releasing the pin from the timer leaves it at whatever level the
    // last toggle happened to end on, and half the time that is HIGH -
    // which is a 5 V step into the amplifier rather than silence, and
    // audible as a thump. Put it back down by hand.
    digitalWrite(pin, LOW);
    _isSinging = false;
  }

private:
  bool _isSinging = false;

  volatile uint8_t* timerControlA() const {
    switch (timer) {
      case 1: return &TCCR1A;
      case 3: return &TCCR3A;
      case 4: return &TCCR4A;
      default: return &TCCR5A;
    }
  }

  volatile uint8_t* timerControlB() const {
    switch (timer) {
      case 1: return &TCCR1B;
      case 3: return &TCCR3B;
      case 4: return &TCCR4B;
      default: return &TCCR5B;
    }
  }

  volatile uint16_t* timerCompare() const {
    switch (timer) {
      case 1: return &OCR1A;
      case 3: return &OCR3A;
      case 4: return &OCR4A;
      default: return &OCR5A;
    }
  }
};


// The five MSGEQ7 modules, read as one.
//
// Ported from Thomas Erforth's `Analyzer::ReadFreq` (Source code/Thomas/
// AudioAnalyzer.cpp), timings and all - they are his measurements against
// the chip's datasheet minimums and are not numbers to round off.
//
// Strobe and reset are commoned across all five modules, so one walk
// through the seven bands hands back a reading for every body at once.
// That is why there is no such thing here as reading one body's
// microphone cheaply: reading one costs what reading five costs, and the
// driver on the other end is written knowing it.
class Analyser {
public:
  void begin() {
    pinMode(ANALYSER_STROBE_PIN, OUTPUT);
    pinMode(ANALYSER_RESET_PIN, OUTPUT);
    digitalWrite(ANALYSER_STROBE_PIN, LOW);
    digitalWrite(ANALYSER_RESET_PIN, LOW);
  }

  // Every band of every module, space separated, module-major - or one
  // module's seven bands when `onlyModule` is 0..4.
  //
  // A bare list of numbers rather than JSON, which is what every other
  // reading on this link is: a light sensor answers with a decimal and
  // nothing else. The whole sweep takes about eight milliseconds, which
  // is a long time to spend not reading the serial port at 1 Mbaud - but
  // this link is strictly one command and one reply, so nothing is
  // arriving while it runs.
  String read(int8_t onlyModule = -1) {
    uint16_t values[ANALYSER_MODULES][ANALYSER_BANDS];
    sweep(values);

    String out;
    out.reserve(ANALYSER_MODULES * ANALYSER_BANDS * 5);
    for (uint8_t module = 0; module < ANALYSER_MODULES; module++) {
      if (onlyModule >= 0 && module != onlyModule) continue;
      for (uint8_t band = 0; band < ANALYSER_BANDS; band++) {
        if (out.length()) out += ' ';
        out += values[module][band];
      }
    }
    return out;
  }

private:
  void reset() {
    digitalWrite(ANALYSER_STROBE_PIN, LOW);
    digitalWrite(ANALYSER_RESET_PIN, LOW);
    digitalWrite(ANALYSER_RESET_PIN, HIGH);  // tr, 100 ns min, 28 us measured
    digitalWrite(ANALYSER_RESET_PIN, LOW);
    delayMicroseconds(54);  // tRS, reset low to strobe low, 72 us min
  }

  void step() {
    digitalWrite(ANALYSER_STROBE_PIN, HIGH);
    delayMicroseconds(18);                   // tS, strobe pulse, 18 us min
    digitalWrite(ANALYSER_STROBE_PIN, LOW);  // tO, output settling, 36 us min
    delayMicroseconds(36);
  }

  void sweep(uint16_t values[ANALYSER_MODULES][ANALYSER_BANDS]) {
    reset();

    // Ten sweeps thrown away before the one that counts. The MSGEQ7 holds
    // a peak with its own decay, so a band that was loud a moment ago is
    // still reading loud; walking it round ten times first is what makes
    // the inactive bands fall. Thomas's number, and the reason a reading
    // taken immediately after a tone changes is not to be trusted.
    for (uint8_t i = 0; i < 10 * ANALYSER_BANDS; i++) step();

    for (uint8_t band = 0; band < ANALYSER_BANDS; band++) {
      step();
      for (uint8_t module = 0; module < ANALYSER_MODULES; module++) {
        values[module][band] = analogRead(ANALYSER_FIRST_ADC + module);
      }
    }
  }
};


class PixelGroup {
public:
  Adafruit_NeoPixel* strip;
  int startPixel;
  int numPixels;

  PixelGroup(Adafruit_NeoPixel* strip, int startPixel, int numPixels)
    : strip(strip), startPixel(startPixel), numPixels(numPixels) {}

  String fill(JsonDocument& doc) {
    for (int i = startPixel; i < startPixel + numPixels; i++) {
      int r = doc["r"] | 0;
      int g = doc["g"] | 0;
      int b = doc["b"] | 0;
      int w = doc["w"] | 0;
      strip->setPixelColor(i,
                           strip->Color(
                             r,
                             g,
                             b,
                             w));
    }
    strip->show();
    return "";
  }
};

class PixelGroupBeam {
public:
  Adafruit_NeoPixel* strip;
  int startPixel;
  int numPixels;

  PixelGroupBeam(Adafruit_NeoPixel* strip, int startPixel, int numPixels)
    : strip(strip), startPixel(startPixel), numPixels(numPixels) {}

  String fill(JsonDocument& doc) {
    for (int i = startPixel; i < startPixel + numPixels; i += 2) {
      int r = doc["r"] | 0;
      int g = doc["g"] | 0;
      int b = doc["b"] | 0;
      int w = doc["w"] | 0;
      strip->setPixelColor(i,
                           strip->Color(
                             r,
                             g,
                             b,
                             w));
    }
    strip->show();
    return "";
  }
};

class PixelGroupForFemaleBody {
public:
  Adafruit_NeoPixel* strip;
  int startPixel;
  int numPixels;

  PixelGroupForFemaleBody(Adafruit_NeoPixel* strip, int startPixel, int numPixels)
    : strip(strip), startPixel(startPixel), numPixels(numPixels) {}

  String fill(JsonDocument& doc) {
    for (int i = startPixel; i < startPixel + numPixels; i += 2) {
      int r = doc["r"] | 0;
      int g = doc["g"] | 0;
      int b = doc["b"] | 0;
      int w = doc["w"] | 0;
      strip->setPixelColor(i,
                           strip->Color(
                             r,
                             g,
                             b,
                             w));
    }
    strip->show();
    return "";
  }
};

class Female {
public:
  PixelGroup head;
  PixelGroupForFemaleBody bodyO;
  PixelGroupForFemaleBody bodyP;
  PixelGroup feet;
  LightSensor lightSensor;

  Female(PixelGroup& head, PixelGroupForFemaleBody& bodyO, PixelGroupForFemaleBody& bodyP, PixelGroup& feet, LightSensor& lightSensor)
    : head(head),
      bodyO(bodyO),
      bodyP(bodyP),
      feet(feet),
      lightSensor(lightSensor) {}
};

class Male {
public:
  PixelGroup upRing;
  PixelGroup ring;
  PixelGroupBeam beam;
  PixelGroup pDriveLevel;
  PixelGroup oDriveLevel;
  LightSensor lightSensorA;
  LightSensor lightSensorB;
  LightSensor lightSensorC;
  LightSensor lightSensorD;

  Male(PixelGroup& upRing, PixelGroup& ring, PixelGroupBeam& beam, PixelGroup& pDriveLevel, PixelGroup& oDriveLevel,
        LightSensor& lightSensorA, LightSensor& lightSensorB, LightSensor& lightSensorC, 
        LightSensor& lightSensorD)
    : upRing(upRing),
      ring(ring),
      beam(beam),
      pDriveLevel(pDriveLevel),
      oDriveLevel(oDriveLevel),
      lightSensorA(lightSensorA),
      lightSensorB(lightSensorB),
      lightSensorC(lightSensorC),
      lightSensorD(lightSensorD) {}
};
// ##########################################################

// ##########################################################
// Object initialisation
Adafruit_NeoPixel female1Strip(
  FEMALE_NUM_PIXELS,
  FEMALE1_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

PixelGroup head1(&female1Strip, 37, 13);
PixelGroupForFemaleBody bodyO1(&female1Strip, 0, 27);
PixelGroupForFemaleBody bodyP1(&female1Strip, 1, 28);
PixelGroup feet1(&female1Strip, 29, 7);
LightSensor lightSensor1(59);

Female female1(head1, bodyO1, bodyP1, feet1, lightSensor1);

Adafruit_NeoPixel female2Strip(
  FEMALE_NUM_PIXELS,
  FEMALE2_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

PixelGroup head2(&female2Strip, 37, 13);
PixelGroupForFemaleBody bodyO2(&female2Strip, 0, 27);
PixelGroupForFemaleBody bodyP2(&female2Strip, 1, 28);
PixelGroup feet2(&female2Strip, 29, 7);
LightSensor lightSensor2(60);

Female female2(head2, bodyO2, bodyP2, feet2, lightSensor2);

Adafruit_NeoPixel female3Strip(
  FEMALE_NUM_PIXELS,
  FEMALE3_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

PixelGroup head3(&female3Strip, 37, 13);
PixelGroupForFemaleBody bodyO3(&female3Strip, 8, 27);
PixelGroupForFemaleBody bodyP3(&female3Strip, 9, 28);
PixelGroup feet3(&female3Strip, 0, 7);
LightSensor lightSensor3(61);

Female female3(head3, bodyO3, bodyP3, feet3, lightSensor3);

Female females[] = {
  female1,
  female2,
  female3
};

Adafruit_NeoPixel male1UpRingStrip(
  24,
  MALE1_UP_RING_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

Adafruit_NeoPixel male1Strip(
  NUMBER_OF_PIXEL_IN_MALE_BODY,
  MALE1_BODY_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

PixelGroup upRing1(&male1UpRingStrip, 0, 24);
PixelGroup ring1(&male1Strip, 0, 24);
PixelGroupBeam beam1(&male1Strip, 0, 24);
PixelGroup pDriveLevel1(&male1Strip, 24, 8);
PixelGroup oDriveLevel1(&male1Strip, 32, 8);


LightSensor lightSensorA1(A8);
LightSensor lightSensorB1(A9);
LightSensor lightSensorC1(A10);
LightSensor lightSensorD1(A11);

Male male1(upRing1, ring1, beam1, pDriveLevel1, oDriveLevel1,
        lightSensorA1, lightSensorB1, lightSensorC1, 
        lightSensorD1);

Adafruit_NeoPixel male2UpRingStrip(
  24,
  MALE2_UP_RING_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

Adafruit_NeoPixel male2Strip(
  NUMBER_OF_PIXEL_IN_MALE_BODY,
  MALE2_BODY_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

PixelGroup upRing2(&male2UpRingStrip, 0, 24);
PixelGroup ring2(&male2Strip, 0, 24);
PixelGroupBeam beam2(&male2Strip, 0, 24);
PixelGroup pDriveLevel2(&male2Strip, 24, 8);
PixelGroup oDriveLevel2(&male2Strip, 32, 8);


LightSensor lightSensorA2(A12);
LightSensor lightSensorB2(A13);
LightSensor lightSensorC2(A14);
LightSensor lightSensorD2(A15);

Male male2(upRing2, ring2, beam2, pDriveLevel2, oDriveLevel2,
        lightSensorA2, lightSensorB2, lightSensorC2, 
        lightSensorD2);

Male males[] = {
  male1,
  male2,
};

Adafruit_NeoPixel strips[] = {
  female1Strip,
  female2Strip,
  female3Strip,
  male1Strip,
  male2Strip,
  male1UpRingStrip,
  male2UpRingStrip,
};

// The five voices, in body order - which is the order of the analyser
// modules, because the board put female1..male2's microphones on A0..A4
// and the modules took their place. One number still identifies a body
// round the whole loop.
//
// It is no longer ascending pitch, and that is the change of 2026-08-27:
// the males hold the two low voices. Pitch order is male1, male2,
// female1, female2, female3.
//
// The OCR values are Thomas's (AudioAnalyzer.h, OCRVALS16), and they are
// indexed by *timer* - which is why the bodies moved across the pins
// rather than the pitches moving across the bodies. They are not the
// exactly-calculated ones: he trimmed them against a counter, so the
// tones come out at 162, 405, 1012, 2531 and 6329 Hz. Each is comfortably
// inside its own analyser band and nowhere near a neighbouring one, which
// is all the accuracy this needs.
Voice female1Voice(FEMALE1_TONE_PIN, 4, 1000, 0x1EE4);
Voice female2Voice(FEMALE2_TONE_PIN, 5, 2500, 0x0C58);
Voice female3Voice(FEMALE3_TONE_PIN, 2, 6250, 0x009D);
Voice male1Voice(MALE1_TONE_PIN, 1, 160, 0xC0F7);
Voice male2Voice(MALE2_TONE_PIN, 3, 400, 0x4D31);

Voice* voices[] = {
  &female1Voice,
  &female2Voice,
  &female3Voice,
  &male1Voice,
  &male2Voice,
};

Analyser analyser;
// ##########################################################

// Who this board is, in one line the driver can parse. Sent once on
// reboot, and again whenever it is asked for ("version"), so the check
// can be repeated without power-cycling the installation.
String greeting() {
  return String("{\"hello\":\"colloquy of mobiles\",\"firmware\":")
         + FIRMWARE_VERSION
         + ",\"baudrate\":"
         + SERIAL_BAUDRATE
         + "}";
}

void setup() {
  for (auto& strip : strips) {
    strip.begin();
    strip.show();
  }

  // Silent first, and deliberately before anything else can take time
  // over it. A Mega comes out of reset with its timers cleared, so this
  // is not undoing anything the chip did - it is putting every tone pin
  // low and known, so that a body cannot be left humming by a sketch that
  // failed to start properly.
  for (auto* voice : voices) {
    voice->begin();
  }
  analyser.begin();

  Serial.begin(SERIAL_BAUDRATE);
  // Each time the serial port is opened the Arduino is rebooted, so this
  // line is how the driver knows the board is ready. Since it says which
  // firmware and which baud rate, it is also how the driver knows this is
  // the board it was written for.
  Serial.println(greeting());
}

// The line being collected right now. At 1 Mbaud a whole command lands in
// under a millisecond and the core's receive buffer holds 64 bytes, so
// there is no time to spare while it arrives: readStringUntil() used to
// build the line one String concatenation at a time - a fresh allocation
// per character - which is slower than the bytes come in and would
// silently lose the tail of a command. A fixed buffer never allocates.
char commandBuffer[COMMAND_BUFFER_SIZE];
uint8_t commandLength = 0;

void loop() {
  while (Serial.available()) {
    char character = Serial.read();
    if (character == '\r') continue;
    if (character == '\n') {
      commandBuffer[commandLength] = '\0';
      Serial.println(processCommand(commandBuffer));
      commandLength = 0;
      continue;
    }
    // Anything past the end is dropped rather than allowed to run off the
    // buffer. The line is then junk, and deserializeJson() says so.
    if (commandLength < COMMAND_BUFFER_SIZE - 1) {
      commandBuffer[commandLength++] = character;
    }
  }
}

String processCommand(const char* input) {
  // Analyse du JSON
  StaticJsonDocument<256> jsonDoc;
  DeserializationError error = deserializeJson(jsonDoc, input);
  if (error) {
    return "Error while deserializeJson!";
  }

  // Returning nothing at all from a function declared to return a String
  // is undefined behaviour, and this used to do exactly that.
  if (!jsonDoc.containsKey("path")) return "No path in command!";

  String path = jsonDoc["path"];

  // Asked for by the driver, and offered on the page. It sits in the same
  // if-chain as everything else on purpose: the simulator learns which
  // paths exist by reading them out of this file.
  if (path == "version") {
    return greeting();
  }

  // Every module at once. One sweep of the commoned strobe reads all five
  // bodies, so this costs exactly what "f1/microphone" costs and returns
  // five times as much - which is why anything reading more than one body
  // should ask for this one instead. Thirty-five numbers, module-major,
  // in body order: female1, female2, female3, male1, male2.
  if (path == "microphones") {
    return analyser.read();
  }

  // Everything quiet, in one command. Worth having as its own path rather
  // than as five: it is what a shutdown, an emergency stop and a failed
  // run all want, and none of them is in a position to send five commands
  // and check five replies.
  if (path == "speakers/off") {
    for (auto* voice : voices) {
      voice->silence();
    }
    return "";
  }

  if (path == "f1/head") {
    return female1.head.fill(jsonDoc);
  } else if (path == "f1/bodyO") {
    return female1.bodyO.fill(jsonDoc);
  } else if (path == "f1/bodyP") {
    return female1.bodyP.fill(jsonDoc);
  } else if (path == "f1/feet") {
    return female1.feet.fill(jsonDoc);
  } else if (path == "f1/light sensor") {
    return female1.lightSensor.read();
  } else if (path == "f1/speaker") {
    return female1Voice.set(jsonDoc);
  } else if (path == "f1/microphone") {
    return analyser.read(0);
  } 
  
  
  else if (path == "f2/head") {
    return female2.head.fill(jsonDoc);
  } else if (path == "f2/bodyO") {
    return female2.bodyO.fill(jsonDoc);
  } else if (path == "f2/bodyP") {
    return female2.bodyP.fill(jsonDoc);
  } else if (path == "f2/feet") {
    return female2.feet.fill(jsonDoc);
  } else if (path == "f2/light sensor") {
    return female2.lightSensor.read();
  } else if (path == "f2/speaker") {
    return female2Voice.set(jsonDoc);
  } else if (path == "f2/microphone") {
    return analyser.read(1);
  }  
  
  
  else if (path == "f3/head") {
    return female3.head.fill(jsonDoc);
  } else if (path == "f3/bodyO") {
    return female3.bodyO.fill(jsonDoc);
  } else if (path == "f3/bodyP") {
    return female3.bodyP.fill(jsonDoc);
  } else if (path == "f3/feet") {
    return female3.feet.fill(jsonDoc);
  } else if (path == "f3/light sensor") {
    return female3.lightSensor.read();
  } else if (path == "f3/speaker") {
    return female3Voice.set(jsonDoc);
  } else if (path == "f3/microphone") {
    return analyser.read(2);
  } 
  
  
  else if (path == "m1/ring") {
    return male1.ring.fill(jsonDoc);
  } else if (path == "m1/up ring") {
    return male1.upRing.fill(jsonDoc);
  } else if (path == "m1/beam") {
    return male1.beam.fill(jsonDoc);
  } else if (path == "m1/p drive level") {
    return male1.pDriveLevel.fill(jsonDoc);
  } else if (path == "m1/o drive level") {
    return male1.oDriveLevel.fill(jsonDoc);
  } else if (path == "m1/light sensor/a") {
    return male1.lightSensorA.read();
  }  else if (path == "m1/light sensor/b") {
    return male1.lightSensorB.read();
  }  else if (path == "m1/light sensor/c") {
    return male1.lightSensorC.read();
  }  else if (path == "m1/light sensor/d") {
    return male1.lightSensorD.read();
  } else if (path == "m1/speaker") {
    return male1Voice.set(jsonDoc);
  } else if (path == "m1/microphone") {
    return analyser.read(3);
  } 

  
  else if (path == "m2/ring") {
    return male2.ring.fill(jsonDoc);
  } else if (path == "m2/up ring") {
    return male2.upRing.fill(jsonDoc);
  } else if (path == "m2/beam") {
    return male2.beam.fill(jsonDoc);
  } else if (path == "m2/p drive level") {
    return male2.pDriveLevel.fill(jsonDoc);
  } else if (path == "m2/o drive level") {
    return male2.oDriveLevel.fill(jsonDoc);
  } else if (path == "m2/light sensor/a") {
    return male2.lightSensorA.read();
  }  else if (path == "m2/light sensor/b") {
    return male2.lightSensorB.read();
  }  else if (path == "m2/light sensor/c") {
    return male2.lightSensorC.read();
  }  else if (path == "m2/light sensor/d") {
    return male2.lightSensorD.read();
  } else if (path == "m2/speaker") {
    return male2Voice.set(jsonDoc);
  } else if (path == "m2/microphone") {
    return analyser.read(4);
  }

  // Falling off the end of a String-returning function is undefined
  // behaviour, and this chain used to do exactly that for any path it did
  // not recognise. An unknown path is now said out loud, which is what a
  // renamed pixel group looks like from the Python side.
  return String("Unknown path: ") + path;
}



