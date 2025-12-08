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

  PixelGroup(Adafruit_NeoPixel* strip, int startPixel, int numPixels)
    : strip(strip), startPixel(startPixel), numPixels(numPixels) {}

  void fill(JsonDocument& doc) {
    for (int i = startPixel; i < startPixel + numPixels; i++) {
      int r = doc["r"] | 0;
      int g = doc["g"] | 0;
      int b = doc["b"] | 0;
      int w = doc["w"] | 0;
      strip->setPixelColor(i,
                           strip->Color(
                             r,
                             g,
                             b,
                             w));
    }
    strip->show();
  }
};

class PixelGroupForFemaleBody {
public:
  Adafruit_NeoPixel* strip;
  int startPixel;
  int numPixels;

  PixelGroupForFemaleBody(Adafruit_NeoPixel* strip, int startPixel, int numPixels)
    : strip(strip), startPixel(startPixel), numPixels(numPixels) {}

  void fill(JsonDocument& doc) {
    for (int i = startPixel; i < startPixel + numPixels; i += 2) {
      int r = doc["r"] | 0;
      int g = doc["g"] | 0;
      int b = doc["b"] | 0;
      int w = doc["w"] | 0;
      strip->setPixelColor(i,
                           strip->Color(
                             r,
                             g,
                             b,
                             w));
    }
    strip->show();
  }
};

class Female {
public:
  PixelGroup head;
  PixelGroupForFemaleBody bodyO;
  PixelGroupForFemaleBody bodyP;
  PixelGroup feet;

  Female(PixelGroup& head, PixelGroupForFemaleBody& bodyO, PixelGroupForFemaleBody& bodyP, PixelGroup& feet)
    : head(head),
      bodyO(bodyO),
      bodyP(bodyP),
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
PixelGroupForFemaleBody bodyO1(&female1Strip, 0, 27);
PixelGroupForFemaleBody bodyP1(&female1Strip, 1, 28);
PixelGroup feet1(&female1Strip, 29, 7);

Female female1(head1, bodyO1, bodyP1, feet1);
// ##########################################################

void setup() {
  female1Strip.begin();
  female1Strip.show();

  test1();

  Serial.begin(57600);
  // Each time the serial port is opened the Arduino is rebooted.
  // The arduino will be ready when client can read "Hello!" on the serial.
  Serial.println("Hello!");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    processCommand(input);
  }
}

void processCommand(const String& input) {
  // Analyse du JSON
  StaticJsonDocument<256> jsonDoc;
  DeserializationError error = deserializeJson(jsonDoc, input);
  if (error) {
    return ;
  }

  if (!jsonDoc.containsKey("path")) return ;

  String path = jsonDoc["path"];

  if (path == "f1/head") {
    return female1.head.fill(jsonDoc);
  } else if (path == "f1/bodyO") {
    return female1.bodyO.fill(jsonDoc);
  } else if (path == "f1/bodyP") {
    return female1.bodyP.fill(jsonDoc);
  } else if (path == "f1/feet") {
    return female1.feet.fill(jsonDoc);
  }
}

void test1(){
  // Create a reusable JSON doc for test colors
  StaticJsonDocument<64> jsonDoc;
  
  jsonDoc["r"] = 255;
  jsonDoc["g"] = 0;
  jsonDoc["b"] = 0;
  jsonDoc["w"] = 0;
  female1.head.fill(jsonDoc);
  delay(500);
  
  jsonDoc["r"] = 0;
  jsonDoc["g"] = 0;
  jsonDoc["b"] = 255;
  jsonDoc["w"] = 0; 
  female1.bodyO.fill(jsonDoc);
  delay(500);
  
  jsonDoc["r"] = 0;
  jsonDoc["g"] = 255;
  jsonDoc["b"] = 0;
  jsonDoc["w"] = 0;
  female1.bodyP.fill(jsonDoc);
  delay(500);
  
  jsonDoc["r"] = 255;
  jsonDoc["g"] = 0;
  jsonDoc["b"] = 0;
  jsonDoc["w"] = 0;
  female1.feet.fill(jsonDoc);
  delay(500);

  // ------------------------------------------
  jsonDoc["r"] = 0;
  jsonDoc["g"] = 0;
  jsonDoc["b"] = 0;
  jsonDoc["w"] = 0;
  female1.head.fill(jsonDoc);
  delay(500);
  
  jsonDoc["r"] = 0;
  jsonDoc["g"] = 0;
  jsonDoc["b"] = 0;
  jsonDoc["w"] = 0; 
  female1.bodyO.fill(jsonDoc);
  delay(500);
  
  jsonDoc["r"] = 0;
  jsonDoc["g"] = 0;
  jsonDoc["b"] = 0;
  jsonDoc["w"] = 0;  
  female1.bodyP.fill(jsonDoc);
  delay(500);
  
  jsonDoc["r"] = 0;
  jsonDoc["g"] = 0;
  jsonDoc["b"] = 0;
  jsonDoc["w"] = 0;
  female1.feet.fill(jsonDoc);
  delay(500);
}



