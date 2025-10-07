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
Adafruit_NeoPixel female2Strip(
  FEMALE_NUM_PIXELS,
  FEMALE2_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel female3Strip(
  FEMALE_NUM_PIXELS,
  FEMALE3_NEOPIXEL_PIN,
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
Adafruit_NeoPixel male2BodyStrip(
  NUMBER_OF_PIXEL_IN_MALE_BODY,
  MALE2_BODY_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

#define NUMBER_OF_PIXEL_IN_MALE_UP_RING 24  // Nombre de LEDs par groupe
Adafruit_NeoPixel male1UpRingStrip(
  NUMBER_OF_PIXEL_IN_MALE_UP_RING,
  MALE1_UP_RING_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel male2UpRingStrip(
  NUMBER_OF_PIXEL_IN_MALE_UP_RING,
  MALE2_UP_RING_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

// Configuration des haut-parleurs pour chaque groupe
#define FEMALE1_SPEAKER_PIN 11
#define FEMALE2_SPEAKER_PIN 12
#define FEMALE3_SPEAKER_PIN 13
#define MALE1_SPEAKER_PIN 22
#define MALE2_SPEAKER_PIN 23

// Config for photosensors
#define FEMALE1_PHOTOSENSOR_PIN 59  // What is A5 pin number ?
#define FEMALE2_PHOTOSENSOR_PIN 60  // What is A6 pin number ?
#define FEMALE3_PHOTOSENSOR_PIN 61  // What is A7 pin number ?

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

class Female {
public:
  String name;
  Adafruit_NeoPixel* strip;
  int speakerPin;
  // int numPixels;
  PixelGroup head;
  PixelGroup body;
  PixelGroup feet;

  Female(String name, Adafruit_NeoPixel* strip, int speakerPin, int numPixels)
    : name(name), 
    head(strip, 37, 13), 
    body(strip, 0, 28), 
    feet(strip, 29, 7), 
    speakerPin(speakerPin) {}

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

  String sensor(int pin) {
    int value = analogRead(pin);
    String result = "{\"status\": \"success\", \"value\": ";
    result += value;
    result += "}";
    return result;
  }
};

class Female3 {
public:
  String name;
  Adafruit_NeoPixel* strip;
  int speakerPin;
  // int numPixels;
  PixelGroup head;
  PixelGroup body;
  PixelGroup feet;

  Female3(String name, Adafruit_NeoPixel* strip, int speakerPin, int numPixels)
    : name(name), 
    head(strip, 37, 13), 
    body(strip, 8, 28), 
    feet(strip, 0, 7), 
    speakerPin(speakerPin) {}

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

  String sensor(int pin) {
    int value = analogRead(pin);
    String result = "{\"status\": \"success\", \"value\": ";
    result += value;
    result += "}";
    return result;
  }
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
  int speakerPin;
  // int numPixels;
  MaleBody body;
  PixelGroup upRing;

  Male(String name, Adafruit_NeoPixel* bodyStrip, Adafruit_NeoPixel* upRingStrip, int speakerPin)
    : name(name),
      upRing(upRingStrip, 0, NUMBER_OF_PIXEL_IN_MALE_UP_RING),
      speakerPin(speakerPin),
      body(bodyStrip),
      bodyStrip(bodyStrip),
      upRingStrip(upRingStrip) {}

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
Female3 female3("female3", &female3Strip, FEMALE3_SPEAKER_PIN, FEMALE_NUM_PIXELS);
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

  if (path == "female1/speaker") {
    return female1.speaker(jsonDoc);
  } else if (path == "female1/sensor") {
    return female1.sensor(FEMALE1_PHOTOSENSOR_PIN);
  } else if (path == "female1/head neopixel") {
    return female1.head.fill(jsonDoc);
  } else if (path == "female1/body neopixel") {
    return female1.body.fill(jsonDoc);
  } else if (path == "female1/feet neopixel") {
    return female1.feet.fill(jsonDoc);
  }

  else if (path == "female2/speaker") {
    return female2.speaker(jsonDoc);
  } else if (path == "female2/head neopixel") {
    return female2.head.fill(jsonDoc);
  } else if (path == "female2/sensor") {
    return female2.sensor(FEMALE2_PHOTOSENSOR_PIN);
  } else if (path == "female2/body neopixel") {
    return female2.body.fill(jsonDoc);
  } else if (path == "female2/feet neopixel") {
    return female2.feet.fill(jsonDoc);
  }

  else if (path == "female3/speaker") {
    return female3.speaker(jsonDoc);
  } else if (path == "female3/head neopixel") {
    return female3.head.fill(jsonDoc);
  } else if (path == "female3/sensor") {
    return female3.sensor(FEMALE3_PHOTOSENSOR_PIN);
  } else if (path == "female3/body neopixel") {
    return female3.body.fill(jsonDoc);
  } else if (path == "female3/feet neopixel") {
    return female3.feet.fill(jsonDoc);
  }

  else if (path == "male1/speaker") {
    return male1.speaker(jsonDoc);
  } else if (path == "male1/up_ring") {
    return male1.upRing.fill(jsonDoc);
  } else if (path == "male1/body/o_drive") {
    return male1.body.o_drive.fill(jsonDoc);
  } else if (path == "male1/body/p_drive") {
    return male1.body.p_drive.fill(jsonDoc);
  } else if (path == "male1/body/ring") {
    return male1.body.ring.fill(jsonDoc);
  }

  else if (path == "male2/speaker") {
    return male2.speaker(jsonDoc);
  } else if (path == "male2/up_ring") {
    return male2.upRing.fill(jsonDoc);
  } else if (path == "male2/body/o_drive") {
    return male2.body.o_drive.fill(jsonDoc);
  } else if (path == "male2/body/p_drive") {
    return male2.body.p_drive.fill(jsonDoc);
  } else if (path == "male2/body/ring") {
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
