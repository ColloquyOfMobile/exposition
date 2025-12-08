#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>
// Configuration des Neopixels pour chaque groupe
// PINs
#define FEMALE1_NEOPIXEL_PIN 6

#define FEMALE_NUM_PIXELS 50  // Nombre de LEDs par groupe

// Initialisation des bandes Neopixel
Adafruit_NeoPixel female1Strip(
  FEMALE_NUM_PIXELS,
  FEMALE1_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);


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
  String name;
  Adafruit_NeoPixel* strip;
  // int numPixels;
  PixelGroup head;
  PixelGroup body;
  PixelGroup feet;

  Female(String name, Adafruit_NeoPixel* strip, int numPixels)
    : name(name),
      head(strip, 37, 13),
      body(strip, 0, 28),
      feet(strip, 29, 7) {}
};

Female female1("female1", &female1Strip, FEMALE_NUM_PIXELS);

void setup() {
  // Initialisation des Neopixels
  female1Strip.begin();

  female1Strip.show();


  // Initialisation du port série
  Serial.begin(57600);
  // Each time the serial port is opened the Arduino is rebooted.
  // The arduino will be ready when client can read "Hello!" on the serial.
  Serial.println("Hello!");
}

void loop() {
  if (Serial.available()) {
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
}




