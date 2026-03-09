#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>

// PINs
#define FEMALE1_NEOPIXEL_PIN 6
#define FEMALE2_NEOPIXEL_PIN 7
#define FEMALE3_NEOPIXEL_PIN 8

#define FEMALE_NUM_PIXELS 50  // Female LED number

#define MALE1_BODY_NEOPIXEL_PIN 9
#define MALE2_BODY_NEOPIXEL_PIN 10
#define MALE1_UP_RING_NEOPIXEL_PIN 5
#define MALE2_UP_RING_NEOPIXEL_PIN 4

#define NUMBER_OF_PIXEL_IN_MALE_BODY 40

// ##########################################################
// Class definitions

class LightSensor{
public:
  const int pin;
  LightSensor(int pin) : pin(pin) {}
  String read(){
    int value = analogRead(pin);
    return String(value);
  }

};

class PixelGroup {
public:
  Adafruit_NeoPixel* strip;
  int startPixel;
  int numPixels;

  PixelGroup(Adafruit_NeoPixel* strip, int startPixel, int numPixels)
    : strip(strip), startPixel(startPixel), numPixels(numPixels) {}

  String fill(JsonDocument& doc) {
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
    return "";
  }
};

class PixelGroupBeam {
public:
  Adafruit_NeoPixel* strip;
  int startPixel;
  int numPixels;

  PixelGroupBeam(Adafruit_NeoPixel* strip, int startPixel, int numPixels)
    : strip(strip), startPixel(startPixel), numPixels(numPixels) {}

  String fill(JsonDocument& doc) {
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
    return "";
  }
};

class PixelGroupForFemaleBody {
public:
  Adafruit_NeoPixel* strip;
  int startPixel;
  int numPixels;

  PixelGroupForFemaleBody(Adafruit_NeoPixel* strip, int startPixel, int numPixels)
    : strip(strip), startPixel(startPixel), numPixels(numPixels) {}

  String fill(JsonDocument& doc) {
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
    return "";
  }
};

class Female {
public:
  PixelGroup head;
  PixelGroupForFemaleBody bodyO;
  PixelGroupForFemaleBody bodyP;
  PixelGroup feet;
  LightSensor lightSensor;

  Female(PixelGroup& head, PixelGroupForFemaleBody& bodyO, PixelGroupForFemaleBody& bodyP, PixelGroup& feet, LightSensor& lightSensor)
    : head(head),
      bodyO(bodyO),
      bodyP(bodyP),
      feet(feet),
      lightSensor(lightSensor) {}
};

class Male {
public:
  PixelGroup upRing;
  PixelGroup ring;
  PixelGroupBeam beam;
  PixelGroup pDriveLevel;
  PixelGroup oDriveLevel;
  LightSensor lightSensorA;
  LightSensor lightSensorB;
  LightSensor lightSensorC;
  LightSensor lightSensorD;

  Male(PixelGroup& upRing, PixelGroup& ring, PixelGroupBeam& beam, PixelGroup& pDriveLevel, PixelGroup& oDriveLevel,
        LightSensor& lightSensorA, LightSensor& lightSensorB, LightSensor& lightSensorC, 
        LightSensor& lightSensorD)
    : upRing(upRing),
      ring(ring),
      beam(beam),
      pDriveLevel(pDriveLevel),
      oDriveLevel(oDriveLevel),
      lightSensorA(lightSensorA),
      lightSensorB(lightSensorB),
      lightSensorC(lightSensorC),
      lightSensorD(lightSensorD) {}
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
LightSensor lightSensor1(59);

Female female1(head1, bodyO1, bodyP1, feet1, lightSensor1);

Adafruit_NeoPixel female2Strip(
  FEMALE_NUM_PIXELS,
  FEMALE2_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

PixelGroup head2(&female2Strip, 37, 13);
PixelGroupForFemaleBody bodyO2(&female2Strip, 0, 27);
PixelGroupForFemaleBody bodyP2(&female2Strip, 1, 28);
PixelGroup feet2(&female2Strip, 29, 7);
LightSensor lightSensor2(60);

Female female2(head2, bodyO2, bodyP2, feet2, lightSensor2);

Adafruit_NeoPixel female3Strip(
  FEMALE_NUM_PIXELS,
  FEMALE3_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

PixelGroup head3(&female3Strip, 37, 13);
PixelGroupForFemaleBody bodyO3(&female3Strip, 8, 27);
PixelGroupForFemaleBody bodyP3(&female3Strip, 9, 28);
PixelGroup feet3(&female3Strip, 0, 7);
LightSensor lightSensor3(61);

Female female3(head3, bodyO3, bodyP3, feet3, lightSensor3);

Female females[] = {
  female1,
  female2,
  female3
};

Adafruit_NeoPixel male1UpRingStrip(
  24,
  4,
  NEO_GRBW + NEO_KHZ800);

Adafruit_NeoPixel male1Strip(
  NUMBER_OF_PIXEL_IN_MALE_BODY,
  MALE1_BODY_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

PixelGroup upRing1(&male1UpRingStrip, 0, 24);
PixelGroup ring1(&male1Strip, 0, 24);
PixelGroupBeam beam1(&male1Strip, 0, 24);
PixelGroup pDriveLevel1(&male1Strip, 24, 8);
PixelGroup oDriveLevel1(&male1Strip, 32, 8);


LightSensor lightSensorA1(A8);
LightSensor lightSensorB1(A9);
LightSensor lightSensorC1(A10);
LightSensor lightSensorD1(A11);

Male male1(upRing1, ring1, beam1, pDriveLevel1, oDriveLevel1,
        lightSensorA1, lightSensorB1, lightSensorC1, 
        lightSensorD1);

Adafruit_NeoPixel male2UpRingStrip(
  24,
  5,
  NEO_GRBW + NEO_KHZ800);

Adafruit_NeoPixel male2Strip(
  NUMBER_OF_PIXEL_IN_MALE_BODY,
  MALE2_BODY_NEOPIXEL_PIN,
  NEO_GRBW + NEO_KHZ800);

PixelGroup upRing2(&male2UpRingStrip, 0, 24);
PixelGroup ring2(&male1Strip, 0, 24);
PixelGroupBeam beam2(&male1Strip, 0, 24);
PixelGroup pDriveLevel2(&male1Strip, 24, 8);
PixelGroup oDriveLevel2(&male1Strip, 32, 8);


LightSensor lightSensorA2(A12);
LightSensor lightSensorB2(A13);
LightSensor lightSensorC2(A14);
LightSensor lightSensorD2(A15);

Male male2(upRing2, ring2, beam2, pDriveLevel2, oDriveLevel2,
        lightSensorA2, lightSensorB2, lightSensorC2, 
        lightSensorD2);

Male males[] = {
  male1,
  male2,
};
// ##########################################################

void setup() {
  for (auto& f : females) {
    f.head.strip -> begin();
    f.head.strip -> show();
  }

  Serial.begin(57600);
  // Each time the serial port is opened the Arduino is rebooted.
  // The arduino will be ready when client can read "Hello!" on the serial.
  Serial.println("Hello!");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    String response = processCommand(input);
    Serial.println(response);
  }
}

String processCommand(const String& input) {
  // Analyse du JSON
  StaticJsonDocument<256> jsonDoc;
  DeserializationError error = deserializeJson(jsonDoc, input);
  if (error) {
    return "Error while deserializeJson!";
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
  } else if (path == "f1/light sensor") {
    return female1.lightSensor.read();
  } 
  
  
  else if (path == "f2/head") {
    return female2.head.fill(jsonDoc);
  } else if (path == "f2/bodyO") {
    return female2.bodyO.fill(jsonDoc);
  } else if (path == "f2/bodyP") {
    return female2.bodyP.fill(jsonDoc);
  } else if (path == "f2/feet") {
    return female2.feet.fill(jsonDoc);
  } else if (path == "f2/light sensor") {
    return female1.lightSensor.read();
  }  
  
  
  else if (path == "f3/head") {
    return female3.head.fill(jsonDoc);
  } else if (path == "f3/bodyO") {
    return female3.bodyO.fill(jsonDoc);
  } else if (path == "f3/bodyP") {
    return female3.bodyP.fill(jsonDoc);
  } else if (path == "f3/feet") {
    return female3.feet.fill(jsonDoc);
  } else if (path == "f3/light sensor") {
    return female1.lightSensor.read();
  } 
  
  
  else if (path == "m1/ring") {
    return male1.ring.fill(jsonDoc);
  } else if (path == "m1/beam") {
    return male1.beam.fill(jsonDoc);
  } else if (path == "m1/p drive level") {
    return male1.pDriveLevel.fill(jsonDoc);
  } else if (path == "m1/o drive level") {
    return male1.oDriveLevel.fill(jsonDoc);
  } else if (path == "m1/light sensor/a") {
    return male1.lightSensorA.read();
  }  else if (path == "m1/light sensor/b") {
    return male1.lightSensorB.read();
  }  else if (path == "m1/light sensor/c") {
    return male1.lightSensorC.read();
  }  else if (path == "m1/light sensor/d") {
    return male1.lightSensorD.read();
  } 

  
  else if (path == "m2/ring") {
    return male2.ring.fill(jsonDoc);
  } else if (path == "m2/beam") {
    return male2.beam.fill(jsonDoc);
  } else if (path == "m2/p drive level") {
    return male2.pDriveLevel.fill(jsonDoc);
  } else if (path == "m2/o drive level") {
    return male2.oDriveLevel.fill(jsonDoc);
  } else if (path == "m2/light sensor/a") {
    return male2.lightSensorA.read();
  }  else if (path == "m2/light sensor/b") {
    return male2.lightSensorB.read();
  }  else if (path == "m2/light sensor/c") {
    return male2.lightSensorC.read();
  }  else if (path == "m2/light sensor/d") {
    return male2.lightSensorD.read();
  } 
}



