#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <cmath>


//BLE server name
#define bleServerName "ESP32 BT ECG"

float reading;
int wave_frequency = 5; // Hz
int sampling_freq = 200; // Hz

// Timer variables
unsigned long lastTime = 0;
unsigned long timerDelay = 1000/sampling_freq;

bool deviceConnected = false;

// See the following for generating UUIDs:
// https://www.uuidgenerator.net/
#define SERVICE_UUID "91bad492-b950-4226-aa2b-4ede9fa42f59"

// Humidity Characteristic and Descriptor
BLECharacteristic readingCharacteristics("ca73b3ba-39f6-4ab3-91ae-186dc9577d99", BLECharacteristic::PROPERTY_NOTIFY);
BLEDescriptor readingDescriptor(BLEUUID((uint16_t)0x2903));

//Setup callbacks onConnect and onDisconnect
class MyServerCallbacks: public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
  };
  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
  }
};

void setup() {
  // Start serial communication 
  Serial.begin(115200);

  // Create the BLE Device
  BLEDevice::init(bleServerName);

  // Create the BLE Server
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create the BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Reading
  pService->addCharacteristic(&readingCharacteristics);
  readingDescriptor.setValue("Simulated Reading");
  readingCharacteristics.addDescriptor(new BLE2902());
  
  // Start the service
  pService->start();

  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pServer->getAdvertising()->start();
  Serial.println("Waiting a client connection to notify...");
}

void loop() {
  if (deviceConnected) {
    if ((millis() - lastTime) > timerDelay) {
  
      reading = sin(2*M_PI*wave_frequency*0.001*millis());
      
      //Notify humidity reading from BME
      static char readingPacket[6];
      dtostrf(reading, 6, 2, readingPacket);
      //Set humidity Characteristic value and notify connected client
      readingCharacteristics.setValue(readingPacket);
      readingCharacteristics.notify();   
      Serial.print(" - Reading: ");
      Serial.print(reading);
      
      lastTime = millis();
    }
  }
}