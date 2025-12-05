#include <Adafruit_NeoPixel.h>

// === SAME PINS AS YOUR PROGRAM ===
#define PIN_M1_A      9
#define PIN_M2_A      10
#define PIN_M1_B      5
#define PIN_M2_B      4
#define PIN_F1      6
#define PIN_F2      7
#define PIN_F3      8

// === SAME LED COUNTS AS YOUR PROJECT ===
// Change here if needed
#define COUNT_M 50
#define COUNT_F   50

Adafruit_NeoPixel stripM1_A(COUNT_M, PIN_M1_A, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel stripM1_B(COUNT_M, PIN_M1_B, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel stripM2_A(COUNT_M, PIN_M2_A, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel stripM2_B(COUNT_M, PIN_M2_B, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel stripF1   (COUNT_F,    PIN_F1,    NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel stripF2   (COUNT_F,    PIN_F2,    NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel stripF3   (COUNT_F,    PIN_F3,    NEO_GRBW + NEO_KHZ800);

unsigned long testStart;

void setup() {
    Serial.begin(115200);

    stripM1_A.begin();
    stripM1_B.begin();
    stripM2_A.begin();
    stripM2_B.begin();
    stripF1.begin();
    stripF2.begin();
    stripF3.begin();

    stripM1_A.show();
    stripM1_B.show();
    stripM2_A.show();
    stripM2_B.show();
    stripF1.show();
    stripF2.show();
    stripF3.show();

    Serial.println("=== LED STRESS TEST STARTED ===");
    testStart = millis();
}

void showAll() {
    stripM1_A.show();
    stripM1_B.show();
    stripM2_A.show();
    stripM2_B.show();
    stripF1.show();
    stripF2.show();
    stripF3.show();
}

void randomFill(Adafruit_NeoPixel& s) {
    for (int i = 0; i < s.numPixels(); i++) {
        uint8_t r = random(0, 256);
        uint8_t g = random(0, 256);
        uint8_t b = random(0, 256);
        uint8_t w = random(0, 256);
        s.setPixelColor(i, s.Color(r, g, b, w));
    }
}

void fillColor(Adafruit_NeoPixel& s, uint8_t r, uint8_t g, uint8_t b, uint8_t w) {
    for (int i = 0; i < s.numPixels(); i++)
        s.setPixelColor(i, s.Color(r, g, b, w));
}

void loop() {

    // 1) Random colors, updated rapidly
    randomFill(stripM1_A);
    randomFill(stripM1_B);
    randomFill(stripM2_A);
    randomFill(stripM2_B);
    randomFill(stripF1);
    randomFill(stripF2);
    randomFill(stripF3);
    showAll();
    delay(10);

    // 2) Full white blast (highest power)
    fillColor(stripM1_A, 255, 255, 255, 255);
    fillColor(stripM1_B, 255, 255, 255, 255);
    fillColor(stripM2_A, 255, 255, 255, 255);
    fillColor(stripM2_B, 255, 255, 255, 255);
    fillColor(stripF1,    255, 255, 255, 255);
    fillColor(stripF2,    255, 255, 255, 255);
    fillColor(stripF3,    255, 255, 255, 255);
    showAll();
    delay(50);

    // 3) Off
    fillColor(stripM1_A, 0,0,0,0);
    fillColor(stripM1_B, 0,0,0,0);
    fillColor(stripM2_A, 0,0,0,0);
    fillColor(stripM2_B, 0,0,0,0);
    fillColor(stripF1,    0,0,0,0);
    fillColor(stripF2,    0,0,0,0);
    fillColor(stripF3,    0,0,0,0);
    showAll();
    delay(20);

    // 4) Fast strobe on random channels
    uint8_t rr = random(0,256);
    uint8_t gg = random(0,256);
    uint8_t bb = random(0,256);
    uint8_t ww = random(0,256);
    
    fillColor(stripM1_A, rr,gg,bb,ww);
    fillColor(stripM1_B, rr,gg,bb,ww);
    fillColor(stripM2_A, rr,gg,bb,ww);
    fillColor(stripM2_B, rr,gg,bb,ww);
    fillColor(stripF1,    rr,gg,bb,ww);
    fillColor(stripF2,    rr,gg,bb,ww);
    fillColor(stripF3,    rr,gg,bb,ww);
    showAll();
    delay(5);

    // 5) Report performance every 5 seconds
    if (millis() - testStart >= 5000) {
        Serial.println("Still stable after 5 seconds...");
        testStart = millis();
    }
}

