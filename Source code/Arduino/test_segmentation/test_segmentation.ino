#include <Adafruit_NeoPixel.h>

// ---------------------------------------------------
// STRIP DEFINITIONS (pin, count)
// ---------------------------------------------------
Adafruit_NeoPixel s6  (50,  6, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel s7  (50,  7, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel s8  (50,  8, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel s9  (40,  9, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel s10 (40, 10, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel s5  (24,  5, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel s4  (24,  4, NEO_GRBW + NEO_KHZ800);

// Data table for iteration
struct StripInfo {
  Adafruit_NeoPixel* strip;
  int count;
  int pin;
};

StripInfo STRIPS[] = {
  { &s6,  50,  6 },
  { &s7,  50,  7 },
  { &s8,  50,  8 },
  { &s9,  40,  9 },
  { &s10, 40, 10 },
  { &s5,  24,  5 },
  { &s4,  24,  4 }
};

int NUM_STRIPS = sizeof(STRIPS) / sizeof(STRIPS[0]);

// Global rotating segment index
int activeSegment = 0;
unsigned long lastChange = 0;
unsigned long interval = 1000;  // 1 second per highlight


// ---------------------------------------------------
// Helper: compute segment start/end
// ---------------------------------------------------
void getSegmentBounds(int numPixels, int segment, int& start, int& end) {
  int base = numPixels / 3;
  int extra = numPixels % 3;   // remainder pixels

  start = segment * base + min(segment, extra);
  end   = start + base - 1;
  if (segment < extra) end++;  // distribute remaining pixels
}


// ---------------------------------------------------
// Light one strip: all white, one segment red
// ---------------------------------------------------
void showStripWithHighlight(StripInfo& S, int highlightedSegment) {
  Adafruit_NeoPixel* strip = S.strip;
  int n = S.count;

  strip->clear();

  for (int seg = 0; seg < 3; seg++) {
    int start, end;
    getSegmentBounds(n, seg, start, end);

    uint32_t color = (seg == highlightedSegment)
                     ? strip->Color(255, 0, 0, 0)   // red
                     : strip->Color(0, 0, 0, 255);  // white using W channel

    for (int i = start; i <= end; i++) {
      strip->setPixelColor(i, color);
    }
  }

  strip->show();
}


// ---------------------------------------------------
void setup() {
  for (int i = 0; i < NUM_STRIPS; i++) {
    STRIPS[i].strip->begin();
    STRIPS[i].strip->clear();
    STRIPS[i].strip->show();
  }
}


// ---------------------------------------------------
void loop() {

  // Rotate which segment is highlighted every second
  unsigned long now = millis();
  if (now - lastChange > interval) {
    lastChange = now;
    activeSegment = (activeSegment + 1) % 3;
  }

  // Update all strips according to highlighted segment
  for (int i = 0; i < NUM_STRIPS; i++) {
    showStripWithHighlight(STRIPS[i], activeSegment);
  }
}
