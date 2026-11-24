// teensy_check.ino - the first sketch on a Teensy 4.1, and the smallest one
// that says it works.
//
// Flashed by `tests > manual tests > test teensy > flash firmware`, and
// asked by that test's `start`. Nothing else is wired to the Teensy for
// this: it sits on the adapter plate on the backplane, and the USB lead is
// the only thing that talks to it.
//
// Pins driven: the on-board LED (pin 13), and the five tone pins, which
// the adapter's translators (U1, U2, powered from the Teensy's own USB 5 V)
// carry to the backplane's yellow TONE 1-TONE 5 LEDs. The tone pins are
// held low except while `l` asks for them, and only ever driven steady
// (no tone): with no voice card fitted that lights an LED and nothing
// else; a fitted card passes the step on to its body as a click at most.
//
// Board: Teensy 4.1, USB Type "Serial", CPU speed 600 MHz (the defaults).
//
// One line in, one line out, over USB serial (the baud rate is ignored -
// it is USB, not a UART):
//
//   ?          -> teensy_check firmware=2 board=teensy41 f_cpu=600000000
//                 uptime_ms=12345 temp_c=41.3 led=heartbeat tone_leds=off
//   e <text>   -> e <text>          (echo: the round-trip check)
//   b          -> blink fast        (the LED flickers for BLINK_FAST_MS,
//                                    for a person to look at)
//   l          -> tone leds         (TONE 1 to TONE 5 light one at a time,
//                                    TONE_STEP_MS each, then all five for
//                                    TONE_ALL_MS, then dark)
//   l <n>      -> tone led <n>      (TONE n alone, steady for TONE_HOLD_MS,
//                                    so its test pin can be metered)
//   l 0        -> tone leds off
//   anything else -> error commands: ? | e <text> | b | l [0-5]
//
// No greeting on boot: a Teensy does not reboot when its port is opened
// (no DTR reset, unlike a Mega), so a greeting would be missed every time.
// The host asks with `?` instead.
//
// Between commands the LED blinks slowly (HEARTBEAT_MS on, HEARTBEAT_MS
// off): a Teensy blinking like that is running this sketch.

#if !defined(__IMXRT1062__)
#error "teensy_check is for a Teensy 4.x (i.MX RT1062). Pick Tools > Board > Teensy 4.1."
#endif

#define FIRMWARE_VERSION 2
#define BOARD_NAME "teensy41"
#define LED_PIN 13
#define HEARTBEAT_MS 500
#define BLINK_FAST_MS 5000
#define BLINK_FAST_PERIOD_MS 50
#define TONE_STEP_MS 1000
#define TONE_ALL_MS 2000
#define TONE_HOLD_MS 30000
#define LINE_LENGTH 256

// The tone pin of each voice slot, slot 1 first (body order: female1,
// female2, female3, male1, male2). From the adapter's copper; the test
// holds this line to `shields_pinout.connections()`.
static const uint8_t TONE_PINS[] = {2, 4, 5, 6, 28};
#define TONE_SLOTS (sizeof(TONE_PINS) / sizeof(TONE_PINS[0]))

// The die temperature, from the core's tempmon.c (C linkage there).
extern "C" float tempmonGetTemp(void);

static char line[LINE_LENGTH];
static size_t lineLength = 0;
static unsigned long blinkFastUntil = 0;

// What the tone LEDs are doing: off, the chase, or one slot held.
enum ToneMode { TONES_OFF, TONES_CHASE, TONES_HOLD };
static ToneMode toneMode = TONES_OFF;
static unsigned long toneStartedAt = 0;
static unsigned toneHeld = 0;  // 1..TONE_SLOTS while TONES_HOLD

void setup() {
  pinMode(LED_PIN, OUTPUT);
  for (unsigned i = 0; i < TONE_SLOTS; i++) {
    pinMode(TONE_PINS[i], OUTPUT);
    digitalWrite(TONE_PINS[i], LOW);
  }
  Serial.begin(115200);
}

static void reportStatus() {
  Serial.print("teensy_check firmware=");
  Serial.print(FIRMWARE_VERSION);
  Serial.print(" board=");
  Serial.print(BOARD_NAME);
  Serial.print(" f_cpu=");
  Serial.print(F_CPU_ACTUAL);
  Serial.print(" uptime_ms=");
  Serial.print(millis());
  Serial.print(" temp_c=");
  Serial.print(tempmonGetTemp(), 1);
  Serial.print(" led=");
  Serial.print(millis() < blinkFastUntil ? "fast" : "heartbeat");
  Serial.print(" tone_leds=");
  if (toneMode == TONES_CHASE) {
    Serial.println("chase");
  } else if (toneMode == TONES_HOLD) {
    Serial.println(toneHeld);
  } else {
    Serial.println("off");
  }
}

static void handle(const char *command) {
  if (command[0] == '?' && command[1] == '\0') {
    reportStatus();
  } else if (command[0] == 'e' && (command[1] == ' ' || command[1] == '\0')) {
    Serial.println(command);
  } else if (command[0] == 'b' && command[1] == '\0') {
    blinkFastUntil = millis() + BLINK_FAST_MS;
    Serial.println("blink fast");
  } else if (command[0] == 'l' && command[1] == '\0') {
    toneMode = TONES_CHASE;
    toneStartedAt = millis();
    Serial.println("tone leds");
  } else if (command[0] == 'l' && command[1] == ' ' && command[2] == '0' &&
             command[3] == '\0') {
    toneMode = TONES_OFF;
    Serial.println("tone leds off");
  } else if (command[0] == 'l' && command[1] == ' ' && command[2] >= '1' &&
             command[2] <= '0' + (char)TONE_SLOTS && command[3] == '\0') {
    toneMode = TONES_HOLD;
    toneHeld = command[2] - '0';
    toneStartedAt = millis();
    Serial.print("tone led ");
    Serial.println(toneHeld);
  } else {
    Serial.println("error commands: ? | e <text> | b | l [0-5]");
  }
}

static void readCommands() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      line[lineLength] = '\0';
      handle(line);
      lineLength = 0;
      continue;
    }
    if (lineLength < LINE_LENGTH - 1) {
      line[lineLength++] = c;
    }
  }
}

static void driveLed() {
  unsigned long now = millis();
  unsigned long period = now < blinkFastUntil ? BLINK_FAST_PERIOD_MS : HEARTBEAT_MS;
  digitalWriteFast(LED_PIN, (now / period) % 2 ? HIGH : LOW);
}

// Which slots are lit now, as a bit per slot (bit 0 = TONE 1).
static unsigned toneLedsLit() {
  unsigned long elapsed = millis() - toneStartedAt;
  if (toneMode == TONES_CHASE) {
    unsigned long chase = (unsigned long)TONE_STEP_MS * TONE_SLOTS;
    if (elapsed < chase) {
      return 1u << (elapsed / TONE_STEP_MS);
    }
    if (elapsed < chase + TONE_ALL_MS) {
      return (1u << TONE_SLOTS) - 1;
    }
    toneMode = TONES_OFF;
  } else if (toneMode == TONES_HOLD) {
    if (elapsed < TONE_HOLD_MS) {
      return 1u << (toneHeld - 1);
    }
    toneMode = TONES_OFF;
  }
  return 0;
}

static void driveToneLeds() {
  unsigned lit = toneLedsLit();
  for (unsigned i = 0; i < TONE_SLOTS; i++) {
    digitalWrite(TONE_PINS[i], (lit >> i) & 1 ? HIGH : LOW);
  }
}

void loop() {
  readCommands();
  driveLed();
  driveToneLeds();
}
