#include <ArduinoBLE.h>
#include <cmath>
 
#define bleServerName "BLE ECG Server"
#define SERVICE_UUID "91bad492-b950-4226-aa2b-4ede9fa42f59"
#define CHARACTERISTIC_UUID "ca73b3ba-39f6-4ab3-91ae-186dc9577d99"

// Bluetooth® Low Energy Test Data Service
BLEService testDataService(SERVICE_UUID);
 
// Bluetooth® Low Energy Battery Test Data Characteristic
BLECharacteristic testDataChar(CHARACTERISTIC_UUID, BLERead | BLENotify, 200);
// remote clients will be able to get notifications if this characteristic changes

unsigned short value;
int wave_frequency = 2; // Hz
int sampling_freq = 250; // Hz
unsigned long previousMillis = 0;
unsigned int timerDelay = 1000/sampling_freq; // ms

const int bufferSize = 100;  // Adjust the buffer size as needed
unsigned short valueBuffer[bufferSize];
int bufferIndex = 0;

void setup()
{
  Serial.begin(9600);    // initialize serial communication
  while (!Serial);
  pinMode(LED_BLUE, OUTPUT); // initialize the built-in LED pin to indicate when a central is connected
 
  // begin initialization
  if (!BLE.begin()) 
  {
    Serial.println("starting BLE failed!");
    while (1);
  }
 
  BLE.setLocalName(bleServerName);
  BLE.setAdvertisedService(testDataService); // add the service UUID
  testDataService.addCharacteristic(testDataChar);
  BLE.addService(testDataService); // Add the battery service
  Serial.println("Advertising, waiting for connections...");
  BLE.advertise();
}
 
void loop()
{
  // wait for a Bluetooth® Low Energy central
  BLEDevice central = BLE.central();
 
  // if a central is connected to the peripheral:
  if (central)
  {
    Serial.print("Connected to central: ");
    Serial.println(central.address());
    digitalWrite(LED_BLUE, LOW);

    while (central.connected())
    {
      long currentMillis = millis();
      if (currentMillis - previousMillis >= timerDelay)
      {
        previousMillis = currentMillis;
        updateValue();
      }
      if (bufferIndex >= bufferSize) {
        // Transmit the entire buffer over BLE
        sendBufferOverBLE();

        // Reset buffer index
        bufferIndex = 0;
      }
    }
    // when the central disconnects, turn off the LED:
    digitalWrite(LED_BUILTIN, LOW);
    Serial.print("Disconnected from central: ");
    Serial.println(central.address());
  }
}
 
void updateValue()
{
  value = 256*sin(2*M_PI*wave_frequency*0.001*millis()) + 512; 
  Serial.println(value);
  valueBuffer[bufferIndex] = value;
  bufferIndex++;
}

void sendBufferOverBLE() {
  // Create a buffer to hold the entire data
  byte dataBuffer[bufferSize * sizeof(unsigned short)];

  // // Copy sensorBuffer to dataBuffer
  memcpy(dataBuffer, valueBuffer, bufferSize * sizeof(unsigned short));

  // // Transmit the entire buffer over BLE
  testDataChar.writeValue(dataBuffer, bufferSize * sizeof(unsigned short));
}