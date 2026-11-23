// teensy_check.ino - the first sketch on a Teensy 4.1, and the smallest one
// that says it works.
//
// Flashed by `tests > manual tests > test teensy > flash firmware`, and
// asked by that test's `start`. Nothing else is wired to the Teensy for
// this: it sits on the adapter plate on the backplane, and the USB lead is
// the only thing that talks to it. No pin is driven except the on-board
// LED (pin 13), so it is safe whatever the backplane carries.
//
// Board: Teensy 4.1, USB Type "Serial", CPU speed 600 MHz (the defaults).
//
// One line in, one line out, over USB serial (the baud rate is ignored -
// it is USB, not a UART):
//
//   ?          -> teensy_check firmware=1 board=teensy41 f_cpu=600000000
//                 uptime_ms=12345 temp_c=41.3 led=heartbeat
//   e <text>   -> e <text>          (echo: the round-trip check)
//   b          -> blink fast        (the LED flickers for BLINK_FAST_MS,
//                                    for a person to look at)
//   anything else -> error commands: ? | e <text> | b
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

#define FIRMWARE_VERSION 1
#define BOARD_NAME "teensy41"
#define LED_PIN 13
#define HEARTBEAT_MS 500
#define BLINK_FAST_MS 5000
#define BLINK_FAST_PERIOD_MS 50
#define LINE_LENGTH 256

// The die temperature, from the core's tempmon.c (C linkage there).
extern "C" float tempmonGetTemp(void);

static char line[LINE_LENGTH];
static size_t lineLength = 0;
static unsigned long blinkFastUntil = 0;

void setup() {
  pinMode(LED_PIN, OUTPUT);
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
  Serial.println(millis() < blinkFastUntil ? "fast" : "heartbeat");
}

static void handle(const char *command) {
  if (command[0] == '?' && command[1] == '\0') {
    reportStatus();
  } else if (command[0] == 'e' && (command[1] == ' ' || command[1] == '\0')) {
    Serial.println(command);
  } else if (command[0] == 'b' && command[1] == '\0') {
    blinkFastUntil = millis() + BLINK_FAST_MS;
    Serial.println("blink fast");
  } else {
    Serial.println("error commands: ? | e <text> | b");
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

void loop() {
  readCommands();
  driveLed();
}
