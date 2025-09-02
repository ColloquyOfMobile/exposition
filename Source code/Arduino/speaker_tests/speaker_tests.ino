#define FEMALE1_SPEAKER_PIN 11
#define FEMALE2_SPEAKER_PIN 12
#define FEMALE3_SPEAKER_PIN 13
#define MALE1_SPEAKER_PIN 22
#define MALE2_SPEAKER_PIN 23

int pins[] = {
  FEMALE1_SPEAKER_PIN,
  FEMALE2_SPEAKER_PIN,
  FEMALE3_SPEAKER_PIN,
  MALE1_SPEAKER_PIN,
  MALE2_SPEAKER_PIN
};
int pinCount = sizeof(pins) / sizeof(pins[0]);

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < pinCount; i++) {
    pinMode(pins[i], OUTPUT);
    digitalWrite(pins[i], LOW);
  }
  Serial.println("Ready. Send: <pin> <0/1>");
}

void loop() {
  if (Serial.available()) {
    int pin = Serial.parseInt();     // read pin number
    int state = Serial.parseInt();   // read state (0 or 1)

    if (state == 0 || state == 1) {
      digitalWrite(pin, state);
      Serial.print("Pin ");
      Serial.print(pin);
      Serial.print(" set to ");
      Serial.println(state);
    }
  }
}
