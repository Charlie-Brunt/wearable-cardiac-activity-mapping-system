#include <bluefruit.h>
#include <math.h>
#include <cstring>

// Parameters
const int frequency = 2; // Hz
const int sampling_frequency = 250; // Hz
const int bit_depth = 8;
int levels = pow(2, bit_depth) - 1;
int channels = 48;

// Timing
unsigned long previousTx = 0;
unsigned long previousMillis = 0;
unsigned long currentMillis = 0;
const long interval = 1000/sampling_frequency;

// data to send in the throughput test
double reading;
const int bufferSize = 240;  // Adjust the buffer size as needed (max 243)
uint8_t valueBuffer[bufferSize];
int bufferIndex = 0;

// Create a buffer to hold the entire data
byte dataBuffer[bufferSize];

BLEDis bledis; // Device Information Service
BLEUart bleuart; // UART service
BLEBas blebas;  // Battery Service

/**************************************************************************/
/*!
    @brief  Sets up the HW an the BLE module (this function is called
            automatically on startup)
*/
/**************************************************************************/
void setup(void)
{  
  Serial.begin(115200);
  // while ( !Serial ) delay(10);   // for nrf52840 with native usb

  Serial.println("Bluefruit52 ECG Server");
  Serial.println("------------------------------\n");

  // Setup the BLE LED to be enabled on CONNECT
  Bluefruit.autoConnLed(true);
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
  Bluefruit.begin();
  Bluefruit.setTxPower(8); // set Tx Power to +8dB; Check bluefruit.h for supported values
  Bluefruit.Periph.setConnectCallback(connect_callback);
  Bluefruit.Periph.setDisconnectCallback(disconnect_callback);
  Bluefruit.Periph.setConnInterval(6, 12); // 7.5 - 15 ms

  // Configure and Start Device Information Service
  bledis.setManufacturer("Adafruit Industries");
  bledis.setModel("Bluefruit Feather52");
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
  }
}

void updateReading()
{
  currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    // Save the last time the LED blinked
    previousMillis = currentMillis;
    for (int i = 0; i < channels; i++){
      reading = (0.2*sin(2*M_PI*4*frequency*millis()/1000)+0.8*sin(2*M_PI*3*frequency*millis()/1000)+1.2*sin(2*M_PI*1.8*frequency*millis()/1000))/3;
      // reading = 0.5;
      // reading = sin(2*M_PI*frequency*millis()/1000);
      valueBuffer[bufferIndex] = map((reading+1)*levels/2, 0, levels, 0, levels);
      bufferIndex++;
    }
  }
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