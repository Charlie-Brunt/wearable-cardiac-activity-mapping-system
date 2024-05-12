#include <math.h>
#include <Arduino.h>
#include <Adafruit_TinyUSB.h> // for Serial

// Timing
unsigned long previousMillis = 0;
unsigned long currentMillis = 0;

// Parameters
const int sampling_frequency = 1000;
const int bit_depth = 8;
int channels = 5;
const int analogPin = 5;
const int s0Pin = 2;
const int s1Pin = 1;
const int s2Pin = 0;
int channel_order[] = {0, 1, 2, 3, 4}; // Change this to match the order of the channels

void setup() {
  pinMode(s0Pin, OUTPUT);
  pinMode(s1Pin, OUTPUT);
  pinMode(s2Pin, OUTPUT);
  digitalWrite(s0Pin, LOW);
  digitalWrite(s1Pin, LOW);
  digitalWrite(s2Pin, LOW);
  Serial.begin(1000000);
  while ( !Serial ) delay(10);   // for nrf52840 with native usb
}

void loop() {
  // Get a fresh ADC value
  currentMillis = millis();
  if (currentMillis - previousMillis >= 1000/sampling_frequency) {
    previousMillis = currentMillis;
    for (int i = 0; i < channels; i++) {
      selectChannel(channel_order[i]);
      uint16_t value10bit = analogRead(analogPin); // Read a 10-bit value from analog pin A0
      uint8_t value8bit = value10bit >> 2;
      Serial.write(value8bit);
    }
    Serial.println();
  }
}

void selectChannel(int channel) {
  // Convert channel number to binary
  digitalWrite(s0Pin, channel & 0x01);
  digitalWrite(s1Pin, (channel >> 1) & 0x01);
  digitalWrite(s2Pin, (channel >> 2) & 0x01);
}