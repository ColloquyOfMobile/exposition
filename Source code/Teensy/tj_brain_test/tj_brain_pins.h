/* ----------------------------------------------------------------------------
 * tj_brain_pins.h  -  Teensy 4.1 pin map of the "TJ Brain" unit board (rev A)
 *
 * One board per unit (female 1-3, male 1-2, bar). Generated from
 * CAD/KiCad/generator/brain.py - keep both in sync.
 * ----------------------------------------------------------------------------
 */
#pragma once

// ---- Dynamixel X-series TTL bus (Serial1 + direction, 74AHCT1G126 / 74LVC1G125)
#define DXL_SERIAL        Serial1   // RX1 = 0, TX1 = 1
#define DXL_DIR_PIN       2         // HIGH = transmit, LOW = receive (10k pull-down)

// ---- NeoPixel outputs (3.3V -> 5V via 74AHCT125, 330R series)
//      All four pins are Serial TX pins, usable with WS2812Serial (DMA, non blocking)
#define NP1_PIN           8         // TX2  - terminal NP1 + DA-15 pin 13 (main body strip)
#define NP2_PIN           29        // TX7  - terminal NP2 + DA-15 pin 9  (male up ring)
#define NP3_PIN           35        // TX8  - terminal NP3
#define NP4_PIN           24        // TX6  - terminal NP4

// ---- Audio
#define AUDIO_PIN         12        // tone() or MQSL -> RC low pass -> divider -> amp
#define AMP_EN_PIN        5         // TPA2005D1 shutdown (HIGH = on, 100k pull-up)
#define MIC_PIN           A2        // pin 16, MAX9814 output (clamped 0..3.3V)
#define EQ_STROBE_PIN     9         // MSGEQ7 (optional, socketed)
#define EQ_RESET_PIN      10
#define EQ_OUT_PIN        A7        // pin 21

// ---- Light sensors (0..5V sensor -> 10k/18k divider -> ADC); LM339 drives LIGHTn LEDs
#define LS1_PIN           A0        // pin 14 - DA-15 pin 5  (female photosensor / male A)
#define LS2_PIN           A1        // pin 15 - DA-15 pin 1  (male B)
#define LS3_PIN           A3        // pin 17 - DA-15 pin 2  (male C)
#define LS4_PIN           A6        // pin 20 - DA-15 pin 3  (male D)
#define AUX_PIN           A8        // pin 22 - DA-15 pin 11 (spare analog, clamped)

// ---- State LED high-side outputs (switched +5V through 150R, PWM capable)
#define STATE1_PIN        3         // JST STATE1 + DA-15 pin 10 (male backlight / beam)
#define STATE2_PIN        4         // JST STATE2

// ---- Unit identity DIP switch SW1 (switch ON pulls to GND -> use INPUT_PULLUP, invert)
#define ID0_PIN           6
#define ID1_PIN           7
#define ID2_PIN           11
#define ID3_PIN           28

// ---- Firmware status LEDs (active HIGH)
#define LED_HEARTBEAT_PIN 30
#define LED_HOST_PIN      31
#define LED_ERROR_PIN     32
#define LED_USER_PIN      37

// ---- Expansion header J2 (2x5): 3V3, 5V, SDA(18), SCL(19), 23(A9), 25(A11), 26, 27, 40(A16), 41(A17)

enum UnitId : uint8_t { UNIT_NONE = 0, UNIT_FEMALE1 = 1, UNIT_FEMALE2 = 2, UNIT_FEMALE3 = 3,
                        UNIT_MALE1 = 4, UNIT_MALE2 = 5, UNIT_BAR = 6 };

static inline uint8_t readUnitId() {
  const uint8_t pins[4] = {ID0_PIN, ID1_PIN, ID2_PIN, ID3_PIN};
  uint8_t id = 0;
  for (uint8_t i = 0; i < 4; i++) {
    pinMode(pins[i], INPUT_PULLUP);
  }
  delayMicroseconds(50);
  for (uint8_t i = 0; i < 4; i++) {
    if (digitalRead(pins[i]) == LOW) id |= (1 << i);   // switch ON = 1
  }
  return id;
}

static inline const char* unitName(uint8_t id) {
  switch (id) {
    case UNIT_FEMALE1: return "female1";
    case UNIT_FEMALE2: return "female2";
    case UNIT_FEMALE3: return "female3";
    case UNIT_MALE1:   return "male1";
    case UNIT_MALE2:   return "male2";
    case UNIT_BAR:     return "bar";
    default:           return "unknown";
  }
}
