/* ----------------------------------------------------------------------------
 * tj_brain_test.ino  -  bring-up test for the TJ Brain board (Teensy 4.1)
 *
 * Libraries: Adafruit_NeoPixel, Dynamixel2Arduino (both in the Arduino library manager).
 * Open the serial monitor (any baud, USB). Every second the sketch prints the unit
 * id, the analog inputs and the Dynamixel ids that answer a ping. It cycles the
 * NeoPixel outputs and beeps, so every activity LED on the board should blink:
 *   NP1..NP4, TONE, DXL TX, DXL BUS, STATE1/2, HB, HOST, ERR, USER.
 * Commands: 't' toggles the tone test, 's' toggles the state outputs.
 * ----------------------------------------------------------------------------
 */
#include <Adafruit_NeoPixel.h>
#include <Dynamixel2Arduino.h>
#include "tj_brain_pins.h"

#define TEST_PIXELS 50
Adafruit_NeoPixel np1(TEST_PIXELS, NP1_PIN, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel np2(12, NP2_PIN, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel np3(TEST_PIXELS, NP3_PIN, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel np4(TEST_PIXELS, NP4_PIN, NEO_GRBW + NEO_KHZ800);
Dynamixel2Arduino dxl(DXL_SERIAL, DXL_DIR_PIN);

uint8_t unitId;
bool toneOn = true, stateOn = true;
uint32_t lastReport = 0, frame = 0;

static uint16_t readMsgeq7(uint16_t bands[7]) {
  digitalWrite(EQ_RESET_PIN, HIGH);
  delayMicroseconds(1);
  digitalWrite(EQ_RESET_PIN, LOW);
  delayMicroseconds(75);
  for (int i = 0; i < 7; i++) {
    digitalWrite(EQ_STROBE_PIN, LOW);
    delayMicroseconds(40);                 // output settling time
    bands[i] = analogRead(EQ_OUT_PIN);
    digitalWrite(EQ_STROBE_PIN, HIGH);
    delayMicroseconds(40);
  }
  return bands[0];
}

void setup() {
  pinMode(LED_HEARTBEAT_PIN, OUTPUT);
  pinMode(LED_HOST_PIN, OUTPUT);
  pinMode(LED_ERROR_PIN, OUTPUT);
  pinMode(LED_USER_PIN, OUTPUT);
  pinMode(STATE1_PIN, OUTPUT);
  pinMode(STATE2_PIN, OUTPUT);
  pinMode(AMP_EN_PIN, OUTPUT);
  digitalWrite(AMP_EN_PIN, HIGH);
  pinMode(EQ_STROBE_PIN, OUTPUT);
  pinMode(EQ_RESET_PIN, OUTPUT);
  digitalWrite(EQ_STROBE_PIN, HIGH);
  analogReadResolution(10);

  unitId = readUnitId();
  np1.begin(); np2.begin(); np3.begin(); np4.begin();
  np1.setBrightness(40); np2.setBrightness(40); np3.setBrightness(40); np4.setBrightness(40);

  dxl.begin(57600);
  dxl.setPortProtocolVersion(2.0);

  Serial.begin(115200);                    // USB: baud rate is ignored by Teensy
  Serial.println("Hello!");
  Serial.print("TJ Brain unit id ");
  Serial.print(unitId);
  Serial.print(" = ");
  Serial.println(unitName(unitId));
  digitalWrite(LED_ERROR_PIN, unitId == 0 || unitId > 6);
}

void loop() {
  uint32_t now = millis();
  digitalWrite(LED_HEARTBEAT_PIN, (now / 500) & 1);
  digitalWrite(LED_HOST_PIN, (bool)Serial);   // true while a host has the port open

  if (Serial.available()) {
    char c = Serial.read();
    if (c == 't') toneOn = !toneOn;
    if (c == 's') stateOn = !stateOn;
  }

  // NeoPixel chase on all four outputs (20 fps)
  if (now / 50 != frame) {
    frame = now / 50;
    uint32_t colors[4] = {np1.Color(255, 0, 0, 0), np1.Color(0, 255, 0, 0), np1.Color(0, 0, 255, 0), np1.Color(0, 0, 0, 255)};
    Adafruit_NeoPixel* strips[4] = {&np1, &np2, &np3, &np4};
    for (int s = 0; s < 4; s++) {
      strips[s]->clear();
      strips[s]->setPixelColor(frame % strips[s]->numPixels(), colors[(frame / 20 + s) % 4]);
      strips[s]->show();
    }
    int phase = (frame / 10) % 4;
    if (toneOn && phase == 0) tone(AUDIO_PIN, 1000); else noTone(AUDIO_PIN);
    analogWrite(STATE1_PIN, stateOn ? (frame * 8) & 255 : 0);
    analogWrite(STATE2_PIN, stateOn ? 255 - ((frame * 8) & 255) : 0);
  }

  if (now - lastReport >= 1000) {
    lastReport = now;
    digitalWrite(LED_USER_PIN, HIGH);
    uint16_t bands[7];
    readMsgeq7(bands);
    Serial.printf("id=%u %s LS1=%d LS2=%d LS3=%d LS4=%d AUX=%d MIC=%d EQ=",
                  unitId, unitName(unitId), analogRead(LS1_PIN), analogRead(LS2_PIN), analogRead(LS3_PIN),
                  analogRead(LS4_PIN), analogRead(AUX_PIN), analogRead(MIC_PIN));
    for (int i = 0; i < 7; i++) Serial.printf("%u%c", bands[i], i < 6 ? ',' : ' ');
    Serial.print("DXL ping:");
    for (uint8_t id = 1; id <= 10; id++) {
      if (dxl.ping(id)) Serial.printf(" %u", id);
    }
    Serial.println();
    digitalWrite(LED_USER_PIN, LOW);
  }
}
