#include <math.h>
#include <Arduino.h>
#include <Adafruit_TinyUSB.h> // for Serial

// LED
const int ledPin = LED_RED;
int ledState = LOW;
unsigned long previousMillis = 0;
const long interval = 500;

// Parameters
const int frequency = 2;
const int sampling_frequency = 100;
const int bit_depth = 8;
int levels = pow(2, bit_depth) - 1;
int channels = 1;
const int analogPin = 5;
const int s0 = 2;
const int s1 = 1;
const int s2 = 0;

void setup() {
  pinMode(ledPin, OUTPUT);
  pinMode(s0, OUTPUT);
  pinMode(s1, OUTPUT);
  pinMode(s2, OUTPUT);
  digitalWrite(s0, LOW);
  digitalWrite(s1, LOW);
  digitalWrite(s2, LOW);
  Serial.begin(1000000);
  while ( !Serial ) delay(10);   // for nrf52840 with native usb
}

void loop() {
  // Get a fresh ADC value

  // double value1 = analogRead(analogPin);
  uint16_t value10bit = analogRead(analogPin); // Read a 10-bit value from analog pin A0
  uint8_t value8bit = value10bit >> 2;
  Serial.write(value8bit);
  Serial.println();
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