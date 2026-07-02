void setup() {
  // put your setup code here, to run once:
  Serial.begin(57600);
}

void loop()
{
    // Serial.print(millis());

    for (uint8_t pin = A0; pin <= A15; pin++)
    {
        Serial.print(',');
        Serial.print(analogRead(pin));
    }

    Serial.println();

    delay(100);
}