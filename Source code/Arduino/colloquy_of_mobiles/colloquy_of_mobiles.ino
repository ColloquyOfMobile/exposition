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

  String path = jsonDoc["path"];

  // Gestion des actions sur les Neopixels
  if (path.endsWith("/neopixel")) {
    int r = jsonDoc["r"] | 0;
    int g = jsonDoc["g"] | 0;
    int b = jsonDoc["b"] | 0;
    int w = jsonDoc["w"] | 0;
    int brightness = jsonDoc["brightness"] | 255;
    return handleNeopixel(path, r, g, b, w, brightness);
  }
  // Gestion des actions sur les haut-parleurs
  else if (path.endsWith("/speaker")) {
    String data = jsonDoc["data"];
    if (data == "on") {
      return handleSpeaker(path, true);
    } else if (data == "off") {
      return handleSpeaker(path, false);
    } 
  }
  
  return R"({"status": "error", "message": "Invalid path or data"})";
}

String handleNeopixel(const String& path, int r, int g, int b, int w, int brightness) {
  Adafruit_NeoPixel* targetStrip = nullptr;
  int startPixel = 0;
  int numPixels = 0;

  if (path == "female1/neopixel") {
    targetStrip = &female1Strip;
    numPixels = FEMALE_NUM_PIXELS;
  } else if (path == "female2/neopixel") {
    targetStrip = &female2Strip;
    numPixels = FEMALE_NUM_PIXELS;
  } else if (path == "female3/neopixel") {
    targetStrip = &female3Strip;
    numPixels = FEMALE_NUM_PIXELS;
  } else if (path == "male1/ring/neopixel") {
    targetStrip = &male1Strip;
    numPixels = 24;
  } else if (path == "male2/ring/neopixel") {
    targetStrip = &male2Strip;
    numPixels = 24;
  } else if (path == "male1/drive/neopixel") {
    targetStrip = &male1Strip;
    startPixel = 24;
    numPixels = 16;
  } else if (path == "male2/drive/neopixel") {
    targetStrip = &male2Strip;
    startPixel = 24;
    numPixels = 16;
  }

  if (targetStrip != nullptr && numPixels > 0) {
    targetStrip->setBrightness(brightness);
    for (int i = startPixel; i < startPixel + numPixels; i++) {
      targetStrip->setPixelColor(i, targetStrip->Color(r, g, b, w));
    }
    targetStrip->show();
    return R"({"status": "success", "message": "Neopixel updated"})";
  }
  return R"({"status": "error", "message": "Invalid Neopixel path"})";
}

String handleSpeaker(const String& path, bool turnOn) {
  int targetPin = -1;

  if (path == "female1/speaker") {
    targetPin = FEMALE1_SPEAKER_PIN;
  } else if (path == "female2/speaker") {
    targetPin = FEMALE2_SPEAKER_PIN;
  } else if (path == "female3/speaker") {
    targetPin = FEMALE3_SPEAKER_PIN;
  } else if (path == "male1/speaker") {
    targetPin = MALE1_SPEAKER_PIN;
  } else if (path == "male2/speaker") {
    targetPin = MALE2_SPEAKER_PIN;
  }

  if (targetPin != -1) {
    if (turnOn) {
      tone(targetPin, 300);  // Joue un son à 300 Hz
    } else {
      noTone(targetPin);  // Arrête le son
    }
    return R"({"status": "success", "message": "Speaker action completed"})";
  }
  return R"({"status": "error", "message": "Invalid speaker path"})";
}




