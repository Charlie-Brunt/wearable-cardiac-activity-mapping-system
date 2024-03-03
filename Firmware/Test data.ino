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
const int sampling_frequency = 250;
const int bit_depth = 8;
int levels = pow(2, bit_depth) - 1;
int channels = 5;


void setup() {
  pinMode(ledPin, OUTPUT);
  Serial.begin(1000000);
  while ( !Serial ) delay(10);   // for nrf52840 with native usb
}

void loop() {
  // Get a fresh ADC value
  for (int i = 0; i < channels; i++) { 
    double reading1 = (0.2*sin(2*M_PI*random(5)*frequency*millis()/1000)+0.8*sin(2*M_PI*random(3)*frequency*millis()/1000)+1.2*sin(2*M_PI*random(2)*frequency*millis()/1000))/3;
    int value1 = map((reading1+1)*127.5, 0, levels, 0, levels);
    Serial.write(value1);
  }

  // Display the results
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