#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>

// PINs
#define FEMALE1_NEOPIXEL_PIN 6
#define FEMALE2_NEOPIXEL_PIN 7
#define FEMALE3_NEOPIXEL_PIN 8

#define FEMALE_NUM_PIXELS 50  // Female LED number


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

Adafruit_NeoPixel female2Strip(
  FEMALE_NUM_PIXELS,
  FEMALE2_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

PixelGroup head2(&female2Strip, 37, 13);
PixelGroupForFemaleBody bodyO2(&female2Strip, 0, 27);
PixelGroupForFemaleBody bodyP2(&female2Strip, 1, 28);
PixelGroup feet2(&female2Strip, 29, 7);

Female female2(head2, bodyO2, bodyP2, feet2);

Adafruit_NeoPixel female3Strip(
  FEMALE_NUM_PIXELS,
  FEMALE3_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

PixelGroup head3(&female3Strip, 37, 13);
PixelGroupForFemaleBody bodyO3(&female3Strip, 0, 27);
PixelGroupForFemaleBody bodyP3(&female3Strip, 1, 28);
PixelGroup feet3(&female3Strip, 29, 7);

Female female3(head3, bodyO3, bodyP3, feet3);

Female females[] = {
  female1,
  female2,
  female3
};
// ##########################################################

void setup() {
  for (auto& f : females) {
    f.head.strip -> begin();
    f.head.strip -> show();
  }
  // female1Strip.begin();
  // female1Strip.show();
  // female1Strip.begin();
  // female1Strip.show();
  // female1Strip.begin();
  // female1Strip.show();

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
  } else if (path == "f2/head") {
    return female2.head.fill(jsonDoc);
  } else if (path == "f2/bodyO") {
    return female2.bodyO.fill(jsonDoc);
  } else if (path == "f2/bodyP") {
    return female2.bodyP.fill(jsonDoc);
  } else if (path == "f2/feet") {
    return female2.feet.fill(jsonDoc);
  } else if (path == "f3/head") {
    return female3.head.fill(jsonDoc);
  } else if (path == "f3/bodyO") {
    return female3.bodyO.fill(jsonDoc);
  } else if (path == "f3/bodyP") {
    return female3.bodyP.fill(jsonDoc);
  } else if (path == "f3/feet") {
    return female3.feet.fill(jsonDoc);
  }
}



