#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>
// Configuration des Neopixels pour chaque groupe
#define FEMALE1_NEOPIXEL_PIN 6
#define FEMALE2_NEOPIXEL_PIN 7
#define FEMALE3_NEOPIXEL_PIN 8
#define MALE1_NEOPIXEL_PIN 9
#define MALE2_NEOPIXEL_PIN 10

#define FEMALE_NUM_PIXELS 50  // Nombre de LEDs par groupe
#define MALE_NUM_PIXELS 40    // Nombre de LEDs par groupe

// Initialisation des bandes Neopixel
Adafruit_NeoPixel female1Strip(FEMALE_NUM_PIXELS, FEMALE1_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel female2Strip(FEMALE_NUM_PIXELS, FEMALE2_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel female3Strip(FEMALE_NUM_PIXELS, FEMALE3_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel male1Strip(MALE_NUM_PIXELS, MALE1_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800);
Adafruit_NeoPixel male2Strip(MALE_NUM_PIXELS, MALE2_NEOPIXEL_PIN, NEO_GRBW + NEO_KHZ800);

// Configuration des haut-parleurs pour chaque groupe
#define FEMALE1_SPEAKER_PIN 11
#define FEMALE2_SPEAKER_PIN 12
#define FEMALE3_SPEAKER_PIN 13
#define MALE1_SPEAKER_PIN 14
#define MALE2_SPEAKER_PIN 15

void updateStrip(Adafruit_NeoPixel* strip, int numPixels, int r, int g, int b, int w, int brightness);

class Female {
public:
  String name;
  Adafruit_NeoPixel* strip;
  int speakerPin;
  int numPixels;

  Female(String name, Adafruit_NeoPixel* strip, int speakerPin, int numPixels)
    : name(name), strip(strip), speakerPin(speakerPin), numPixels(numPixels) {}

  String neopixel(JsonDocument& doc) {
    int r = doc["r"] | 0;
    int g = doc["g"] | 0;
    int b = doc["b"] | 0;
    int w = doc["w"] | 0;
    int brightness = doc["brightness"] | 255;

    updateStrip(strip, numPixels, r, g, b, w, brightness);
    return R"({"status": "success", "message": "Neopixel updated"})";
  }

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
  int numPixels;
  
  MaleBody(Adafruit_NeoPixel* strip, int numPixels)
    : strip(strip), numPixels(numPixels) {}

  String ring(JsonDocument& doc) {
    int r = doc["r"] | 0;
    int g = doc["g"] | 0;
    int b = doc["b"] | 0;
    int w = doc["w"] | 0;
    int brightness = doc["brightness"] | 255;

    updateStrip(strip, numPixels, r, g, b, w, brightness);
    return R"({"status": "success", "message": "Neopixel updated"})";
  }

  String drive(JsonDocument& doc) {
    int r = doc["r"] | 0;
    int g = doc["g"] | 0;
    int b = doc["b"] | 0;
    int w = doc["w"] | 0;
    int brightness = doc["brightness"] | 255;   

    updateStrip(strip, numPixels, r, g, b, w, brightness);
    return R"({"status": "success", "message": "Neopixel updated"})";
  }
};

class Male {
public:
  String name;
  Adafruit_NeoPixel* strip;
  int speakerPin;
  int numPixels;
  MaleBody body;

  Male(String name, Adafruit_NeoPixel* strip, int speakerPin, int numPixels)
    : name(name), strip(strip), speakerPin(speakerPin), numPixels(numPixels), body(strip, numPixels){}



  String upRing(JsonDocument& doc) {
    int r = doc["r"] | 0;
    int g = doc["g"] | 0;
    int b = doc["b"] | 0;
    int w = doc["w"] | 0;
    int brightness = doc["brightness"] | 255;

    updateStrip(strip, numPixels, r, g, b, w, brightness);
    return R"({"status": "success", "message": "Neopixel updated"})";
  }

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

Female* female1;
Female* female2;
Female* female3;
Male* male1;
Male* male2;

void setup() {
  // Initialisation des Neopixels
  female1Strip.begin();
  female2Strip.begin();
  female3Strip.begin();
  male1Strip.begin();
  male2Strip.begin();

  female1Strip.show();
  female2Strip.show();
  female3Strip.show();
  male1Strip.show();
  male2Strip.show();

  // Initialisation des haut-parleurs
  pinMode(FEMALE1_SPEAKER_PIN, OUTPUT);
  pinMode(FEMALE2_SPEAKER_PIN, OUTPUT);
  pinMode(FEMALE3_SPEAKER_PIN, OUTPUT);
  pinMode(MALE1_SPEAKER_PIN, OUTPUT);
  pinMode(MALE2_SPEAKER_PIN, OUTPUT);

  female1 = new Female("female1", &female1Strip, FEMALE1_SPEAKER_PIN, FEMALE_NUM_PIXELS);
  female2 = new Female("female2", &female2Strip, FEMALE2_SPEAKER_PIN, FEMALE_NUM_PIXELS);
  female3 = new Female("female3", &female3Strip, FEMALE3_SPEAKER_PIN, FEMALE_NUM_PIXELS);
  male1 = new Male("male1",   &male1Strip,   MALE1_SPEAKER_PIN,   MALE_NUM_PIXELS);
  male2 = new Male("male2",   &male2Strip,   MALE2_SPEAKER_PIN,   MALE_NUM_PIXELS);

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
    return female1->speaker(jsonDoc);
  } else if (path == "female1/neopixel"){
    return female1->neopixel(jsonDoc);
  } else if (path == "female2/speaker"){
    return female2->speaker(jsonDoc);
  } else if (path == "female2/neopixel"){
    return female2->neopixel(jsonDoc);
  } else if (path == "female3/speaker"){
    return female3->speaker(jsonDoc);
  } else if (path == "female3/neopixel"){
    return female3->neopixel(jsonDoc);
  } else if (path == "male1/speaker"){
    return male1->speaker(jsonDoc);
  } else if (path == "male1/up_ring"){
    return male1->upRing(jsonDoc);
  } else if (path == "male1/body/drive"){
    return male1->body.drive(jsonDoc);
  } else if (path == "male1/body/ring"){
    return male1->body.ring(jsonDoc);
  } else if (path == "male2/speaker"){
    return male2->speaker(jsonDoc);
  } else if (path == "male2/up_ring"){
    return male2->upRing(jsonDoc);
  } else if (path == "male2/body/drive"){
    return male2->body.drive(jsonDoc);
  } else if (path == "male2/body/ring"){
    return male2->body.ring(jsonDoc);
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




