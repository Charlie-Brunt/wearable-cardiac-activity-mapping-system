#include <math.h>
#include <Arduino.h>
#include <Adafruit_TinyUSB.h> // for Serial

// LED
const int ledPin = LED_BLUE;
int ledState = LOW;
unsigned long previousMillis = 0;
const long interval = 500;

// Parameters
const int frequency = 1;
const int sampling_frequency = 200;
const int bit_depth = 8;
int levels = pow(2, bit_depth) - 1;


void setup() {
  pinMode(ledPin, OUTPUT);
  Serial.begin(115200);
  while ( !Serial ) delay(10);   // for nrf52840 with native usb
}

void loop() {
  // Get a fresh ADC value
  double reading = sin(2*M_PI*frequency*millis()/1000);
  int value = map((reading+1)*127.5, 0, levels, 0, levels);

  // Display the results
  Serial.write(value);

  delay(1000/sampling_frequency);
  blinkLED();
}


void blinkLED() {
  unsigned long currentMillis = millis();  // Get the current time

  // Check if it's time to blink the LED
  if (currentMillis - previousMillis >= interval) {
    // Save the last time the LED blinked
    previousMillis = currentMillis;

    // If the LED is off, turn it on. If it's on, turn it off.
    digitalWrite(ledPin, !digitalRead(ledPin));
  }
}