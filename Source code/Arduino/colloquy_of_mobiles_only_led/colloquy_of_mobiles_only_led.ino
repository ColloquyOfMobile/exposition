#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>
// Configuration des Neopixels pour chaque groupe
// PINs
#define FEMALE1_NEOPIXEL_PIN 6

#define FEMALE_NUM_PIXELS 50  // Nombre de LEDs par groupe


// ##########################################################
// Class definitions

class PixelGroup {
public:
  Adafruit_NeoPixel* strip;
  int startPixel;
  int numPixels;
  uint8_t brightness = 255;  // propre au groupe

  PixelGroup(Adafruit_NeoPixel* strip, int startPixel, int numPixels)
    : strip(strip), startPixel(startPixel), numPixels(numPixels) {}

  void setBrightness(uint8_t b) {
    brightness = b;
  }

  String fill(JsonDocument& doc) {
    for (int i = startPixel; i < startPixel + numPixels; i++) {
      int r = doc["r"] | 0;
      int g = doc["g"] | 0;
      int b = doc["b"] | 0;
      int w = doc["w"] | 0;
      int newBrightness = doc["brightness"] | 255;
      setBrightness(newBrightness);
      strip->setPixelColor(i,
                           strip->Color(
                             scaleBrightness(r),
                             scaleBrightness(g),
                             scaleBrightness(b),
                             scaleBrightness(w)));
    }
    strip->show();
    return R"({"status": "success", "message": "Neopixel updated"})";
  }

  void clear() {
    for (int i = startPixel; i < startPixel + numPixels; i++) {
      strip->setPixelColor(i, 0);
    }
    strip->show();
  }
private:
  uint8_t scaleBrightness(uint8_t value) {
    return (uint16_t(value) * brightness) / 255;
  }
};


class Female {
public:
  PixelGroup head;
  PixelGroup body;
  PixelGroup feet;

  Female(PixelGroup& head, PixelGroup& body, PixelGroup& feet)
    : head(head),
      body(body),
      feet(feet) {}
};
// ##########################################################

// ##########################################################
// Object initialisation
Adafruit_NeoPixel female1Strip(
  FEMALE_NUM_PIXELS,
  FEMALE1_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

PixelGroup head1(&female1Strip, 37, 13);
PixelGroup body1(&female1Strip, 0, 28);
PixelGroup feet1(&female1Strip, 37, 13);

Female female1(head1, body1, feet1);
// ##########################################################

void setup() {
  female1Strip.begin();
  female1Strip.show();

  Serial.begin(57600);
  // Each time the serial port is opened the Arduino is rebooted.
  // The arduino will be ready when client can read "Hello!" on the serial.
  Serial.println("Hello!");
}

void loop() {
  // Create a reusable JSON doc for test colors
  StaticJsonDocument<64> jsonDoc;
  
  jsonDoc["r"] = 255;
  jsonDoc["g"] = 0;
  jsonDoc["b"] = 0;
  jsonDoc["w"] = 0;
  jsonDoc["brightness"] = 255;
  female1.head.fill(jsonDoc);
  delay(500);
  
  jsonDoc["r"] = 0;
  jsonDoc["g"] = 255;
  jsonDoc["b"] = 0;
  jsonDoc["w"] = 0;
  jsonDoc["brightness"] = 255;    
  female1.body.fill(jsonDoc);
  delay(500);
  
  jsonDoc["r"] = 0;
  jsonDoc["g"] = 0;
  jsonDoc["b"] = 255;
  jsonDoc["w"] = 0;
  jsonDoc["brightness"] = 255;
  female1.feet.fill(jsonDoc);
  delay(500);

  // ------------------------------------------
  jsonDoc["r"] = 255;
  jsonDoc["g"] = 0;
  jsonDoc["b"] = 0;
  jsonDoc["w"] = 0;
  jsonDoc["brightness"] = 0;
  female1.head.fill(jsonDoc);
  delay(500);
  
  jsonDoc["r"] = 0;
  jsonDoc["g"] = 255;
  jsonDoc["b"] = 0;
  jsonDoc["w"] = 0;
  jsonDoc["brightness"] = 0;    
  female1.body.fill(jsonDoc);
  delay(500);
  
  jsonDoc["r"] = 0;
  jsonDoc["g"] = 0;
  jsonDoc["b"] = 255;
  jsonDoc["w"] = 0;
  jsonDoc["brightness"] = 0;
  female1.feet.fill(jsonDoc);
  delay(500);
}




