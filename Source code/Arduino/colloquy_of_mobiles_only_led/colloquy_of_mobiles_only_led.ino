#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>
// Configuration des Neopixels pour chaque groupe
// PINs
#define FEMALE1_NEOPIXEL_PIN 6
#define FEMALE2_NEOPIXEL_PIN 7
#define FEMALE3_NEOPIXEL_PIN 8
#define MALE1_BODY_NEOPIXEL_PIN 9
#define MALE2_BODY_NEOPIXEL_PIN 10
#define MALE1_UP_RING_NEOPIXEL_PIN 5
#define MALE2_UP_RING_NEOPIXEL_PIN 4

#define FEMALE_NUM_PIXELS 50  // Nombre de LEDs par groupe

// Initialisation des bandes Neopixel
Adafruit_NeoPixel female1Strip(
  FEMALE_NUM_PIXELS,
  FEMALE1_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

#define NUMBER_OF_PIXEL_IN_MALE_BODY_RING 24
#define MALE_BODY_O_DRIVE_START_PIXEL 24
#define NUMBER_OF_PIXEL_IN_MALE_BODY_RING_O_DRIVE 8
#define MALE_BODY_P_DRIVE_START_PIXEL 32  // 25 + 8 + 1

#define NUMBER_OF_PIXEL_IN_MALE_BODY 40  // Nombre de LEDs par groupe
Adafruit_NeoPixel male1BodyStrip(
  NUMBER_OF_PIXEL_IN_MALE_BODY,
  MALE1_BODY_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

#define NUMBER_OF_PIXEL_IN_MALE_UP_RING 24  // Nombre de LEDs par groupe
Adafruit_NeoPixel male1UpRingStrip(
  NUMBER_OF_PIXEL_IN_MALE_UP_RING,
  MALE1_UP_RING_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);


void updateStrip(Adafruit_NeoPixel* strip, int numPixels, int r, int g, int b, int w, int brightness);

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
      int brightness = doc["brightness"] | 255;
      setBrightness(brightness);
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

class PixelGroupAdvance {
public:
  Adafruit_NeoPixel* strip;
  int startPixel;
  int numPixels;
  uint8_t brightness = 255;  // propre au groupe

  PixelGroupAdvance(Adafruit_NeoPixel* strip, int startPixel, int numPixels)
    : strip(strip), startPixel(startPixel), numPixels(numPixels) {}

  void setBrightness(uint8_t b) {
    brightness = b;
  }

  String fill(JsonDocument& doc) {
    for (int i = startPixel; i < startPixel + numPixels; i += 2) {
      int r = doc["r"] | 0;
      int g = doc["g"] | 0;
      int b = doc["b"] | 0;
      int w = doc["w"] | 0;
      int brightness = doc["brightness"] | 255;
      setBrightness(brightness);
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

class FemaleBody {
public:
  Adafruit_NeoPixel* strip;
  // int numPixels;
  PixelGroupAdvance pixel_o;
  PixelGroupAdvance pixel_p;

  FemaleBody(Adafruit_NeoPixel* strip, int startPixelO, int numPixelsO, int startPixelP, int numPixelsP)
    : pixel_o(strip, startPixelO, numPixelsO),
      pixel_p(strip, startPixelP, numPixelsP) {}
};

class Female {
public:
  String name;
  Adafruit_NeoPixel* strip;
  // int numPixels;
  PixelGroup head;
  FemaleBody body;
  PixelGroup feet;

  Female(String name, Adafruit_NeoPixel* strip, int numPixels)
    : name(name),
      head(strip, 37, 13),
      body(strip, 0, 27, 1, 28),
      feet(strip, 29, 7) {}
};



class MaleBody {
public:
  Adafruit_NeoPixel* strip;
  // int numPixels;
  PixelGroup ring;
  PixelGroup o_drive;
  PixelGroup p_drive;

  MaleBody(Adafruit_NeoPixel* strip)
    : ring(strip, 0, NUMBER_OF_PIXEL_IN_MALE_BODY_RING),
      o_drive(strip, MALE_BODY_O_DRIVE_START_PIXEL, NUMBER_OF_PIXEL_IN_MALE_BODY_RING_O_DRIVE),
      p_drive(strip, MALE_BODY_P_DRIVE_START_PIXEL, NUMBER_OF_PIXEL_IN_MALE_BODY) {}
};

class Male {
public:
  String name;
  Adafruit_NeoPixel* bodyStrip;
  Adafruit_NeoPixel* upRingStrip;
  // int numPixels;
  MaleBody body;
  PixelGroup upRing;

  Male(String name, Adafruit_NeoPixel* bodyStrip, Adafruit_NeoPixel* upRingStrip)
    : name(name),
      upRing(upRingStrip, 0, NUMBER_OF_PIXEL_IN_MALE_UP_RING),
      body(bodyStrip),
      bodyStrip(bodyStrip),
      upRingStrip(upRingStrip) {}
};

Female female1("female1", &female1Strip, FEMALE_NUM_PIXELS);
Male male1("male1", &male1BodyStrip, &male1UpRingStrip);

void setup() {
  // Initialisation des Neopixels
  female1Strip.begin();
  male1BodyStrip.begin();
  male1UpRingStrip.begin();

  female1Strip.show();
  male1BodyStrip.show();
  male1UpRingStrip.show();


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

    // -------------------------------
    // 1. female head BLUE
    // -------------------------------
    jsonDoc["r"] = 0;
    jsonDoc["g"] = 0;
    jsonDoc["b"] = 255;
    jsonDoc["w"] = 0;
    jsonDoc["brightness"] = 255;
    female1.head.fill(jsonDoc);
    delay(500);

    // -------------------------------
    // 2. male o_drive BLUE
    // -------------------------------
    male1.body.o_drive.fill(jsonDoc);
    delay(500);

    // -------------------------------
    // 3. female head RED
    // -------------------------------
    jsonDoc["r"] = 255;
    jsonDoc["g"] = 0;
    jsonDoc["b"] = 0;
    jsonDoc["w"] = 0;
    jsonDoc["brightness"] = 255;
    female1.head.fill(jsonDoc);
    delay(500);

    // -------------------------------
    // 4. male o_drive RED
    // -------------------------------
    male1.body.o_drive.fill(jsonDoc);
    delay(500);

    // String input = Serial.readStringUntil('\n');  // Lire la commande
    // String response = processCommand(input);      // Traiter la commande
    // Serial.println(response);                     // Répondre au PC
  }
}

String processCommand(const String& input) {
  // Analyse du JSON
  StaticJsonDocument<256> jsonDoc;
  DeserializationError error = deserializeJson(jsonDoc, input);
  if (error) {
    return R"({"status": "error", "message": "Invalid JSON"})";
  }

  if (!jsonDoc.containsKey("path")) return R"({"status": "error", "message": "Missing path"})";

  String path = jsonDoc["path"];

  if (path == "female1/head neopixel") {
    return female1.head.fill(jsonDoc);
  } else if (path == "female1/body neopixel/O") {
    return female1.body.pixel_o.fill(jsonDoc);
  } else if (path == "female1/body neopixel/P") {
    return female1.body.pixel_p.fill(jsonDoc);
  } else if (path == "female1/feet neopixel") {
    return female1.feet.fill(jsonDoc);
  }


  if (path == "male1/up_ring") {
    return male1.upRing.fill(jsonDoc);
  } else if (path == "male1/body/o_drive") {
    return male1.body.o_drive.fill(jsonDoc);
  } else if (path == "male1/body/p_drive") {
    return male1.body.p_drive.fill(jsonDoc);
  } else if (path == "male1/body/ring") {
    return male1.body.ring.fill(jsonDoc);
  }



  return R"({"status": "error", "message": "Invalid path or data"})";
}

void updateStrip(Adafruit_NeoPixel* strip, int numPixels, int r, int g, int b, int w, int brightness) {
  strip->setBrightness(brightness);
  for (int i = 0; i < numPixels; i++) {
    strip->setPixelColor(i, strip->Color(r, g, b, w));
  }
  strip->show();
}
