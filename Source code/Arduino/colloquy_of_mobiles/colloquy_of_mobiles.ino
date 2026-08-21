#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>

// ##########################################################
// The link, and what the driver on the other end has to agree with.
//
// Both numbers below are read straight out of this file by the Python
// side (colloquy/hardware/arduino/firmware.py), the same way it already
// reads the paths further down, so this is the one place either of them
// is written. They are also sent on the wire in the greeting, so a board
// running something else says so rather than being mistaken for this one.

// Bumped whenever the serial protocol changes in a way that would make an
// older driver misread this board: a renamed path, a reply of a different
// shape. Nothing about such a mismatch is loud on its own - an unknown
// path is answered with an empty line - so the only symptom is a female
// who never sees a pattern, which is why the driver refuses a version it
// was not written for.
//
// 1: the original. Greeted with a bare "Hello!" and ran at 57600.
// 2: greets with JSON saying this version and this baud rate, answers
//    "version" with the same, and runs the link at 1 Mbaud.
#define FIRMWARE_VERSION 2

// As fast as this link will honestly go. The Mega's USART divides its
// 16 MHz exactly at 1 Mbaud (U2X, UBRR = 1), so there is no framing error
// to accumulate, and the 16U2 bridge carries it. 2 Mbaud divides exactly
// too, and is also the rate at which this pair is known to start dropping
// bytes - and a dropped byte here is a light sensor reading that never
// comes back.
//
// It was 57600 until the pattern reading needed the samples: a female
// decodes her sensor by binning readings against a wall clock, and at
// 57600 one round trip cost about 12ms of a 200ms bit. See
// colloquy/light_pattern_timing.py for where the 200ms comes from.
#define SERIAL_BAUDRATE 1000000UL

// One command line, with room to spare: the longest this sketch is sent
// is a four-channel pixel fill, about seventy characters. It is read into
// a fixed buffer rather than a String - see loop().
#define COMMAND_BUFFER_SIZE 128

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
PixelGroup ring2(&male2Strip, 0, 24);
PixelGroupBeam beam2(&male2Strip, 0, 24);
PixelGroup pDriveLevel2(&male2Strip, 24, 8);
PixelGroup oDriveLevel2(&male2Strip, 32, 8);


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

Adafruit_NeoPixel strips[] = {
  female1Strip,
  female2Strip,
  female3Strip,
  male1Strip,
  male2Strip,
  male1UpRingStrip,
  male2UpRingStrip,
};
// ##########################################################

// Who this board is, in one line the driver can parse. Sent once on
// reboot, and again whenever it is asked for ("version"), so the check
// can be repeated without power-cycling the installation.
String greeting() {
  return String("{\"hello\":\"colloquy of mobiles\",\"firmware\":")
         + FIRMWARE_VERSION
         + ",\"baudrate\":"
         + SERIAL_BAUDRATE
         + "}";
}

void setup() {
  for (auto& strip : strips) {
    strip.begin();
    strip.show();
  }

  Serial.begin(SERIAL_BAUDRATE);
  // Each time the serial port is opened the Arduino is rebooted, so this
  // line is how the driver knows the board is ready. Since it says which
  // firmware and which baud rate, it is also how the driver knows this is
  // the board it was written for.
  Serial.println(greeting());
}

// The line being collected right now. At 1 Mbaud a whole command lands in
// under a millisecond and the core's receive buffer holds 64 bytes, so
// there is no time to spare while it arrives: readStringUntil() used to
// build the line one String concatenation at a time - a fresh allocation
// per character - which is slower than the bytes come in and would
// silently lose the tail of a command. A fixed buffer never allocates.
char commandBuffer[COMMAND_BUFFER_SIZE];
uint8_t commandLength = 0;

void loop() {
  while (Serial.available()) {
    char character = Serial.read();
    if (character == '\r') continue;
    if (character == '\n') {
      commandBuffer[commandLength] = '\0';
      Serial.println(processCommand(commandBuffer));
      commandLength = 0;
      continue;
    }
    // Anything past the end is dropped rather than allowed to run off the
    // buffer. The line is then junk, and deserializeJson() says so.
    if (commandLength < COMMAND_BUFFER_SIZE - 1) {
      commandBuffer[commandLength++] = character;
    }
  }
}

String processCommand(const char* input) {
  // Analyse du JSON
  StaticJsonDocument<256> jsonDoc;
  DeserializationError error = deserializeJson(jsonDoc, input);
  if (error) {
    return "Error while deserializeJson!";
  }

  // Returning nothing at all from a function declared to return a String
  // is undefined behaviour, and this used to do exactly that.
  if (!jsonDoc.containsKey("path")) return "No path in command!";

  String path = jsonDoc["path"];

  // Asked for by the driver, and offered on the page. It sits in the same
  // if-chain as everything else on purpose: the simulator learns which
  // paths exist by reading them out of this file.
  if (path == "version") {
    return greeting();
  }

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
    return female2.lightSensor.read();
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
    return female3.lightSensor.read();
  } 
  
  
  else if (path == "m1/ring") {
    return male1.ring.fill(jsonDoc);
  } else if (path == "m1/up ring") {
    return male1.upRing.fill(jsonDoc);
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
  } else if (path == "m2/up ring") {
    return male2.upRing.fill(jsonDoc);
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



