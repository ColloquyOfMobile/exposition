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
  String data = jsonDoc["data"];

  // Gestion des actions sur les Neopixels
  if (path.endsWith("/neopixel")) {
    if (data == "on") {
      return handleNeopixel(path, true);
    } else if (data == "off") {
      return handleNeopixel(path, false);
    }
  }
  // Gestion des actions sur les haut-parleurs
  else if (path.endsWith("/speaker")) {
    if (data == "on") {
      return handleSpeaker(path, true);
    } else if (data == "off") {
      return handleSpeaker(path, false);
    } 
  }
  else if (path.endsWith("/pacman")) {
    return handlePacman(path);
  }
  else if (path.endsWith("/pinkpanther")) {
    return handlePinkPanther(path);
  }
  

  return R"({"status": "error", "message": "Invalid path or data"})";
}

String handleNeopixel(const String& path, bool turnOn) {
  Adafruit_NeoPixel* targetStrip = nullptr;

  if (path == "female1/neopixel") {
    targetStrip = &female1Strip;
  } else if (path == "female2/neopixel") {
    targetStrip = &female2Strip;
  } else if (path == "female3/neopixel") {
    targetStrip = &female3Strip;
  } else if (path == "male1/neopixel") {
    targetStrip = &male1Strip;
  } else if (path == "male2/neopixel") {
    targetStrip = &male2Strip;
  }

  if (targetStrip != nullptr) {
    for (int i = 0; i < targetStrip->numPixels(); i++) {
      targetStrip->setPixelColor(i, turnOn ? targetStrip->Color(0, 0, 0, 255) : targetStrip->Color(0, 0, 0, 0));
    }
    targetStrip->show();
    return R"({"status": "success", "message": "Neopixel action completed"})";
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

String handlePacman(const String& path) {
  int targetPin = -1;

  if (path == "female1/pacman") {
    targetPin = FEMALE1_SPEAKER_PIN;
  } else if (path == "female2/pacman") {
    targetPin = FEMALE2_SPEAKER_PIN;
  } else if (path == "female3/pacman") {
    targetPin = FEMALE3_SPEAKER_PIN;
  } else if (path == "male1/pacman") {
    targetPin = MALE1_SPEAKER_PIN;
  } else if (path == "male2/pacman") {
    targetPin = MALE2_SPEAKER_PIN;
  }

  if (targetPin != -1) {
    playPacman(targetPin);
    return R"({"status": "success", "message": "Pacman song completed"})";
  }
  return R"({"status": "error", "message": "Invalid song path"})";
}

String handlePinkPanther(const String& path) {
  int targetPin = -1;

  if (path == "female1/pinkpanther") {
    targetPin = FEMALE1_SPEAKER_PIN;
  } else if (path == "female2/pinkpanther") {
    targetPin = FEMALE2_SPEAKER_PIN;
  } else if (path == "female3/pinkpanther") {
    targetPin = FEMALE3_SPEAKER_PIN;
  } else if (path == "male1/pinkpanther") {
    targetPin = MALE1_SPEAKER_PIN;
  } else if (path == "male2/pinkpanther") {
    targetPin = MALE2_SPEAKER_PIN;
  }

  if (targetPin != -1) {
    playPinkPanther(targetPin);
    return R"({"status": "success", "message": "Pacman song completed"})";
  }
  return R"({"status": "error", "message": "Invalid song path"})";
}



