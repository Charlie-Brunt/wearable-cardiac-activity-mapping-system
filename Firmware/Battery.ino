// Program to read battery voltage on XIAO board

#include <math.h>
#include <Arduino.h>
#include <Adafruit_TinyUSB.h> // for Serial

#include <Arduino.h>

#define BAT_READ 14            // P0_14 = 14  Reads battery voltage from divider on signal board. (PIN_VBAT is reading voltage divider on XIAO and is program pin 32 / or P0.31)
#define CHARGE_LED 23          // P0_17 = 17  D23   YELLOW CHARGE LED
#define HICHG 22               // P0_13 = 13  D22   Charge-select pin for Lipo for 100 mA instead of default 50mA charge

const double vRef = 3.3; // Assumes 3.3V regulator output is ADC reference voltage
const unsigned int numReadings = 256; // 10-bit ADC readings 0-1023, so the factor is 1024

volatile int BAT_CHRG; //is the battery connected and charging?   5V connected/charging = 0; disconnected = 1


void setup() {
  // put your setup code here, to run once:

  Serial.begin(115200);
  delay(100);

  pinMode (CHARGE_LED, INPUT);  //sets to detetct if charge LED is on or off to see if USB is plugged in
  pinMode (HICHG, OUTPUT);  digitalWrite(HICHG, LOW);  //100 mA charging current if set to LOW and 50mA (actually about 20mA) if set to HIGH
  pinMode(BAT_READ, OUTPUT);  digitalWrite(BAT_READ, LOW);// This is pin P0_14 = 14 and by pullling low to GND it provices path to read on pin 32 (P0,31) PIN_VBAT the voltage from divider on XIAO board
  analogReadResolution(8);           // wireing_analog_nRF52.c:39

  /*
    printf("\nBattery Test compiled by davekw7x on %s at %s\n",   __DATE__, __TIME__);
    printf("Note: PIN_VBAT = %u\n\n", PIN_VBAT);
  */
}

///////////////////////////////////////////////////////////////////////READ LIPO BATTERY////////////////////////////////////////////////////////////////
void readBAT()  {
  unsigned int adcCount = analogRead(PIN_VBAT);//  PIN_VBAT is reading voltage divider on XIAO and is program pin 32 or P0.31??
  double adcVoltage = (adcCount * vRef) / numReadings;
  double vBat = adcVoltage * 3.30014; // Voltage divider from Vbat to ADC  // was set at 1510.0...set your own value to calibrate to actual voltage reading by your voltmeeter
  double level = min(100, 100 * (vBat - 3.2) / (4.17 - 3.2)); // 3.2V to 4.2V
  printf("adcCount = %3u = 0x%03X, adcVoltage = %.3fV, vBat = %.3f, level = %.1f percent\n", adcCount, adcCount, adcVoltage, vBat, level);  delay(10);
  delay(10);
}
///////////////////////////////////////////////////////////////////////END OF READ LIPO BATTERY////////////////////////////////////////////////////////////////


void loop() {
  // put your main code here, to run repeatedly:

 
  BAT_CHRG = digitalRead(CHARGE_LED);  //

  if (BAT_CHRG == 1)  {  //if USB/charger IS NOT plugged in

    // Serial.print("  Battery Charge status =  "); Serial.println(BAT_CHRG);
    Serial.println(" USB -IS NOT- plugged in ");     //do whatever you want here once USB is detected, in order to make sure user knows that battery-read values are now USB-generate
    }

  if (BAT_CHRG == 0) {   ////if USB/charger IS plugged in
     // Serial.print("  Battery Charge status =  "); Serial.println(BAT_CHRG);
     Serial.println(" USB -IS- plugged in ");     //do whatever you want here once USB is detected, in order to make sure user knows that battery-read values are now USB-generated
  }
  
  readBAT();   // loops back to lipo BAT read routine
  
  delay(5000);//delays 5 sec betwen battery readings


}  //END OF LOOP
