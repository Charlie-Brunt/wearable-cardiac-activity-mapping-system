#include <bluefruit.h>
#include <math.h>
#include <cstring>

// Parameters
const int frequency = 2; // Hz
const int sampling_frequency = 250; // Hz
const int bit_depth = 8;
int levels = pow(2, bit_depth) - 1;
int channels = 5;

// Pin Definitions
const int analogPin = 5; // ADC pin
const int s0Pin = 2; // Multiplexer control pins
const int s1Pin = 1; 
const int s2Pin = 0;
int channel_order[] = {3, 2, 0, 4, 1}; // Change this to match the arrangement of the electrodes

// Battery definitions
#define BAT_READ 14            // P0_14 = 14  Reads battery voltage from divider on signal board. (PIN_VBAT is reading voltage divider on XIAO and is program pin 32 / or P0.31)
#define CHARGE_LED 23          // P0_17 = 17  D23   YELLOW CHARGE LED
#define HICHG 22               // P0_13 = 13  D22   Charge-select pin for Lipo for 100 mA instead of default 50mA charge
const double vRef = 3.3; // Assumes 3.3V regulator output is ADC reference voltage
const unsigned int numReadings = 256; // 10-bit ADC readings 0-1023, so the factor is 1024
volatile int CHARGING; //is the battery connected and charging?   5V connected/charging = 0; disconnected = 1

// Timing
unsigned long previousTx = 0;
unsigned long previousMillis = 0;
unsigned long currentMillis = 0;
unsigned long batteryPreviousMillis = 0;
const long interval = 1000/sampling_frequency;

// data to send over BLE
double reading;
const int bufferSize = 240;  // Adjust the buffer size as needed 243
uint8_t valueBuffer[bufferSize];
int bufferIndex = 0;

// Create a buffer to hold the data
byte dataBuffer[bufferSize];

// BLE Services
BLEDis bledis; // Device Information Service
BLEUart bleuart; // UART service
BLEBas blebas;  // Battery Service

/**************************************************************************/
/*!
    @brief  Sets up the HW and the BLE module (this function is called
            automatically on startup)
*/
/**************************************************************************/
void setup(void)
{  
  Serial.begin(115200);
  // while ( !Serial ) delay(10);   // for nrf52840 with native usb

  // Multiplexer setup
  pinMode(s0Pin, OUTPUT);
  pinMode(s1Pin, OUTPUT);
  pinMode(s2Pin, OUTPUT);
  digitalWrite(s0Pin, LOW);
  digitalWrite(s1Pin, LOW);
  digitalWrite(s2Pin, LOW);

  // Battery level setup
  pinMode (CHARGE_LED, INPUT);  //sets to detetct if charge LED is on or off to see if USB is plugged in
  pinMode (HICHG, OUTPUT);  digitalWrite(HICHG, LOW);  //100 mA charging current if set to LOW and 50mA (actually about 20mA) if set to HIGH
  pinMode(BAT_READ, OUTPUT);  digitalWrite(BAT_READ, LOW);// This is pin P0_14 = 14 and by pullling low to GND it provices path to read on pin 32 (P0,31) PIN_VBAT the voltage from divider on XIAO board
  
  // initialise ADC wireing_analog_nRF52.c:73
  analogReference(AR_DEFAULT);        // default 0.6V*6=3.6V  wireing_analog_nRF52.c:73
  analogReadResolution(8);           // wireing_analog_nRF52.c:39

  Serial.println("Bluefruit52 ECG Server");
  Serial.println("------------------------------\n");

  // Setup the BLE LED to be enabled on CONNECT
  if (digitalRead(CHARGE_LED) == 1) {
    Bluefruit.autoConnLed(true);
  }
  else {
    Bluefruit.autoConnLed(false);
  }
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
  Bluefruit.begin();
  Bluefruit.setTxPower(4); // set Tx Power to +4dB; Check bluefruit.h for supported values
  Bluefruit.Periph.setConnectCallback(connect_callback);
  Bluefruit.Periph.setDisconnectCallback(disconnect_callback);
  Bluefruit.Periph.setConnInterval(6, 12); // 7.5 - 15 ms

  // Configure and Start Device Information Service
  bledis.setManufacturer("SEEED");
  bledis.setModel("Seeed XIAO nRF52840");
  bledis.begin();

  // Configure and Start BLE Uart Service
  bleuart.begin();

  // Configure and Start Battery Service
  blebas.begin();
  blebas.write(100); // (100% battery life)

  // Set up and start advertising
  startAdv();
}


void startAdv(void)
{
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();

  // Include bleuart 128-bit uuid
  Bluefruit.Advertising.addService(bleuart);

  // There is no room for Name in Advertising packet
  // Use Scan response for Name
  Bluefruit.ScanResponse.addName();
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);    // in unit of 0.625 ms
  Bluefruit.Advertising.setFastTimeout(30);      // number of seconds in fast mode
  Bluefruit.Advertising.start(0);                // 0 = Don't stop advertising after n seconds  
}


void connect_callback(uint16_t conn_handle)
{
  BLEConnection* conn = Bluefruit.Connection(conn_handle);
  Serial.println("Connected");

  char central_name[32] = { 0 };
  conn->getPeerName(central_name, sizeof(central_name));
  Serial.print("Connected to ");
  Serial.println(central_name);

  // request PHY changed to 2MB
  Serial.println("Request to change PHY");
  conn->requestPHY();

  // request to update data length
  Serial.println("Request to change Data Length");
  conn->requestDataLengthUpdate();
    
  // request mtu exchange
  Serial.println("Request to change MTU");
  conn->requestMtuExchange(247);

  // request connection interval of 7.5 ms
  // conn->requestConnectionParameter(6); // in unit of 1.25

  // delay a bit for all the requests to complete
  delay(1000);
}


/**
 * Callback invoked when a connection is dropped
 * @param conn_handle connection where this event happens
 * @param reason is a BLE_HCI_STATUS_CODE which can be found in ble_hci.h
 */
void disconnect_callback(uint16_t conn_handle, uint8_t reason)
{
  (void) conn_handle;
  (void) reason;

  Serial.println();
  Serial.print("Disconnected, reason = 0x"); Serial.println(reason, HEX);
}


void loop(void)
{  
  if (Bluefruit.connected())
  {
    // Get a fresh ADC value when ready
    updateReading();

    if (bufferIndex >= bufferSize - 1) {
      // Transmit the entire buffer over BLE
      sendBufferOverBLE();
      // Reset buffer index
      bufferIndex = 0;
    }

    // Send battery level every 20 seconds
    sendBatteryLevel(); 
  }
}


void updateReading()
{
  if (millis() - previousMillis >= interval) {
    // Save the last time the LED blinked
    previousMillis = millis();
    for (int i = 0; i < channels; i++){
      reading = analogRead(analogPin);
      selectChannel(channel_order[i]);
      valueBuffer[bufferIndex] = reading;
      bufferIndex++;
    }
  }
}


void selectChannel(int channel) {
  // Convert channel number to binary
  digitalWrite(s0Pin, channel & 0x01);
  digitalWrite(s1Pin, (channel >> 1) & 0x01);
  digitalWrite(s2Pin, (channel >> 2) & 0x01);
}


void sendBufferOverBLE() {
  long currentTx = millis(); 
  // Copy sensorBuffer to dataBuffer
  memcpy(dataBuffer, valueBuffer, bufferSize);

  // Transmit the entire buffer over BLE
  bleuart.write(dataBuffer, bufferSize);
  Serial.println((bufferSize*1000)/(currentTx - previousTx));
  previousTx = currentTx;
}

void sendBatteryLevel() {
  if (millis() - batteryPreviousMillis >= 2000) {
    batteryPreviousMillis = millis();
    CHARGING = digitalRead(CHARGE_LED);
    unsigned int adcCount = analogRead(PIN_VBAT);//  PIN_VBAT is reading voltage divider on XIAO and is program pin 32 or P0.31??
    double adcVoltage = (adcCount * vRef) / numReadings;
    double vBat = adcVoltage * 3.30014; // Voltage divider from Vbat to ADC  // was set at 1510.0...set your own value to calibrate to actual voltage reading by your voltmeeter
    double level = 100 * (vBat - 3.2) / (4.2 - 3.2); // 3.2V to 4.2V
    printf("adcCount = %3u = 0x%03X, adcVoltage = %.3fV, vBat = %.3f, level = %.1f percent\n", adcCount, adcCount, adcVoltage, vBat, level);  delay(10);
    blebas.write(level);
  }
}