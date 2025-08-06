#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>
// Configuration des Neopixels pour chaque groupe
#define FEMALE1_NEOPIXEL_PIN 6
#define FEMALE2_NEOPIXEL_PIN 7
#define FEMALE3_NEOPIXEL_PIN 8
#define MALE1_BODY_NEOPIXEL_PIN 9
#define MALE2_BODY_NEOPIXEL_PIN 10
// #define MALE1_UP_RING_NEOPIXEL_PIN 11
// #define MALE2_UP_RING_NEOPIXEL_PIN 12

#define FEMALE_NUM_PIXELS 50  // Nombre de LEDs par groupe
#define MALE_BODY_NUM_PIXELS 40    // Nombre de LEDs par groupe
#define MALE_BODY_RING_END_PIXELS 24    // Nombre de LEDs par groupe
#define MALE_BODY_DRIVE_START_PIXELS 25    // Nombre de LEDs par groupe
#define MALE_UP_RING_NUM_PIXELS 12    // Nombre de LEDs par groupe

// Initialisation des bandes Neopixel
Adafruit_NeoPixel female1Strip(FEMALE_NUM_PIXELS, FEMALE1_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel female2Strip(FEMALE_NUM_PIXELS, FEMALE2_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel female3Strip(FEMALE_NUM_PIXELS, FEMALE3_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel male1UpRingStrip(MALE_UP_RING_NUM_PIXELS, MALE1_UP_RING_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel male1BodyStrip(MALE_BODY_NUM_PIXELS, MALE1_BODY_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel male2UpRingStrip(MALE_UP_RING_NUM_PIXELS, MALE2_UP_RING_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel male2BodyStrip(MALE_BODY_NUM_PIXELS, MALE2_BODY_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800);

// Configuration des haut-parleurs pour chaque groupe
#define FEMALE1_SPEAKER_PIN 11
#define FEMALE2_SPEAKER_PIN 12
#define FEMALE3_SPEAKER_PIN 13
#define MALE1_SPEAKER_PIN 14
#define MALE2_SPEAKER_PIN 15

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
          scaleBrightness(w)
        )
      );
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
  int speakerPin;
  // int numPixels;
  PixelGroup neopixel;

  Female(String name, Adafruit_NeoPixel* strip, int speakerPin, int numPixels)
    : name(name), neopixel(strip, 0, FEMALE_NUM_PIXELS), speakerPin(speakerPin) {}

  // String neopixel(JsonDocument& doc) {
  //   int r = doc["r"] | 0;
  //   int g = doc["g"] | 0;
  //   int b = doc["b"] | 0;
  //   int w = doc["w"] | 0;
  //   int brightness = doc["brightness"] | 255;

  //   updateStrip(strip, numPixels, r, g, b, w, brightness);
  //   return R"({"status": "success", "message": "Neopixel updated"})";
  // }

  String speaker(JsonDocument& doc) {
    String data = doc["data"];
    if (data == "on") {
      tone(speakerPin, 300);
    } else {
      noTone(speakerPin);
    }
    return R"({"status": "success", "message": "Speaker updated"})";
  }
};

class MaleBody {
public:
  Adafruit_NeoPixel* strip;
  // int numPixels;
  PixelGroup ring;
  PixelGroup drive;
  
  MaleBody(Adafruit_NeoPixel* strip)
    : ring(strip, 0, MALE_BODY_RING_END_PIXELS), drive(strip, MALE_BODY_DRIVE_START_PIXELS, MALE_BODY_NUM_PIXELS) {}
};

class Male {
public:
  String name;
  Adafruit_NeoPixel* bodyStrip;
  Adafruit_NeoPixel* upRingStrip;
  int speakerPin;
  // int numPixels;
  MaleBody body;
  PixelGroup upRing;

  Male(String name, Adafruit_NeoPixel* bodyStrip, Adafruit_NeoPixel* upRingStrip, int speakerPin)
    : name(name), 
    upRing(upRingStrip, 0, MALE_UP_RING_NUM_PIXELS), 
    speakerPin(speakerPin), 
    body(bodyStrip),
    bodyStrip(bodyStrip),
    upRingStrip(upRingStrip){}

  // String upRing(JsonDocument& doc) {
  //   int r = doc["r"] | 0;
  //   int g = doc["g"] | 0;
  //   int b = doc["b"] | 0;
  //   int w = doc["w"] | 0;
  //   int brightness = doc["brightness"] | 255;

  //   updateStrip(strip, numPixels, r, g, b, w, brightness);
  //   return R"({"status": "success", "message": "Neopixel updated"})";
  // }

  String speaker(JsonDocument& doc) {
    String data = doc["data"];
    if (data == "on") {
      tone(speakerPin, 300);
    } else {
      noTone(speakerPin);
    }
    return R"({"status": "success", "message": "Speaker updated"})";
  }
};

Female female1("female1", &female1Strip, FEMALE1_SPEAKER_PIN, FEMALE_NUM_PIXELS);
Female female2("female2", &female2Strip, FEMALE2_SPEAKER_PIN, FEMALE_NUM_PIXELS);
Female female3("female3", &female3Strip, FEMALE3_SPEAKER_PIN, FEMALE_NUM_PIXELS);
Male male1("male1", &male1BodyStrip, &male1UpRingStrip, MALE1_SPEAKER_PIN);
Male male2("male2", &male2BodyStrip, &male2UpRingStrip, MALE2_SPEAKER_PIN);

void setup() {
  // Initialisation des Neopixels
  female1Strip.begin();
  female2Strip.begin();
  female3Strip.begin();
  male1BodyStrip.begin();
  male2BodyStrip.begin();
  male1UpRingStrip.begin();
  male2UpRingStrip.begin();

  female1Strip.show();
  female2Strip.show();
  female3Strip.show();
  male1BodyStrip.show();
  male2BodyStrip.show();
  male1UpRingStrip.show();
  male2UpRingStrip.show();

  // Initialisation des haut-parleurs
  pinMode(FEMALE1_SPEAKER_PIN, OUTPUT);
  pinMode(FEMALE2_SPEAKER_PIN, OUTPUT);
  pinMode(FEMALE3_SPEAKER_PIN, OUTPUT);
  pinMode(MALE1_SPEAKER_PIN, OUTPUT);
  pinMode(MALE2_SPEAKER_PIN, OUTPUT);

  // Initialisation du port série
  Serial.begin(57600);
  // Each time the serial port is opened the Arduino is rebooted.
  // The arduino will be ready when client can read "Hello!" on the serial.
  Serial.println("Hello!");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');  // Lire la commande
    String response = processCommand(input);      // Traiter la commande
    Serial.println(response);                     // Répondre au PC
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

  if (path == "female1/speaker"){
    return female1.speaker(jsonDoc);
  } else if (path == "female1/neopixel"){
    return female1.neopixel.fill(jsonDoc);
  } else if (path == "female2/speaker"){
    return female2.speaker(jsonDoc);
  } else if (path == "female2/neopixel"){
    return female2.neopixel.fill(jsonDoc);
  } else if (path == "female3/speaker"){
    return female3.speaker(jsonDoc);
  } else if (path == "female3/neopixel"){
    return female3.neopixel.fill(jsonDoc);
  } else if (path == "male1/speaker"){
    return male1.speaker(jsonDoc);
  } else if (path == "male1/up_ring"){
    return male1.upRing.fill(jsonDoc);
  } else if (path == "male1/body/drive"){
    return male1.body.drive.fill(jsonDoc);
  } else if (path == "male1/body/ring"){
    return male1.body.ring.fill(jsonDoc);
  } else if (path == "male2/speaker"){
    return male2.speaker(jsonDoc);
  } else if (path == "male2/up_ring"){
    return male2.upRing.fill(jsonDoc);
  } else if (path == "male2/body/drive"){
    return male2.body.drive.fill(jsonDoc);
  } else if (path == "male2/body/ring"){
    return male2.body.ring.fill(jsonDoc);
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




