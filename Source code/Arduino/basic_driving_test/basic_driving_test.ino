#include <Adafruit_NeoPixel.h>

// Configuration NeoPixels
#define PIXEL_PIN 6           // Broche de données des NeoPixels
#define NUM_PIXELS 42          // Nombre de NeoPixels (modifiez selon votre matériel)
Adafruit_NeoPixel pixels(NUM_PIXELS, PIXEL_PIN, NEO_GRBW + NEO_KHZ800); // Pour RGBW

// Configuration Audio
int audioPin = 9;             // Broche PWM pour l'audio

void setup() {
  pinMode(audioPin, OUTPUT);  // Configure la broche audio
  pixels.begin();             // Initialise les NeoPixels
  pixels.clear();             // Éteint tous les pixels
}

void loop() {
  // Génère un son sur la broche audio
  tone(audioPin, 300);       // Son à 1000 Hz
  setPixelColor(255, 0, 0, 0);  // Pixels rouges (pas de blanc)
  delay(500);                 // Maintient pendant 500 ms

  noTone(audioPin);           // Stoppe le son
  setPixelColor(0, 255, 0, 0);  // Pixels verts (pas de blanc)
  delay(500);                 // Pause de 500 ms

  setPixelColor(0, 0, 0, 255);  // Pixels blancs purs
  delay(500);                 // Maintient pendant 500 ms
}

// Fonction pour changer la couleur de tous les NeoPixels
void setPixelColor(int red, int green, int blue, int white) {
  for (int i = 0; i < NUM_PIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(red, green, blue, white));
  }
  pixels.show();              // Actualise les couleurs
}
