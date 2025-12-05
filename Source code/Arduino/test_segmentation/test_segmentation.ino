#include <Adafruit_NeoPixel.h>

// Strip definitions
Adafruit_NeoPixel s6 (50,  6, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel s7 (50,  7, NEO_GRBW + NEO_KHZ800);
// pin 8 has no strip
Adafruit_NeoPixel s9 (40,  9, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel s10(40, 10, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel s5 (24,  5, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel s4 (24,  4, NEO_GRBW + NEO_KHZ800);

// Simple struct for iteration
struct StripInfo {
  Adafruit_NeoPixel* strip;
  int num;
  int pin;
};

StripInfo strips[] = {
  { &s6,  50,  6 },
  { &s7,  50,  7 },
  // skip pin 8
  { &s9,  40,  9 },
  { &s10, 40, 10 },
  { &s5,  24,  5 },
  { &s4,  24,  4 }
};

int NUM_STRIPS = sizeof(strips) / sizeof(strips[0]);

void setup() {
  Serial.begin(115200);
  Serial.println("Starting segmentation test...");

  for (int i = 0; i < NUM_STRIPS; i++) {
    strips[i].strip->begin();
    strips[i].strip->show(); // clear
  }
}

// Light a single pixel on one strip
void testStrip(StripInfo& S) {
  Serial.print("Testing strip on pin ");
  Serial.print(S.pin);
  Serial.print(" with ");
  Serial.print(S.num);
  Serial.println(" LEDs...");

  for (int i = 0; i < S.num; i++) {
    S.strip->clear();

    // light pixel i in RED
    S.strip->setPixelColor(i, S.strip->Color(255, 0, 0, 0));
    S.strip->show();

    delay(50); // enough to see each pixel
  }

  // turn off after the test
  S.strip->clear();
  S.strip->show();
  delay(300);
}

void loop() {
  // test each strip one by one
  for (int i = 0; i < NUM_STRIPS; i++) {
    testStrip(strips[i]);
  }

  delay(1000);
}
