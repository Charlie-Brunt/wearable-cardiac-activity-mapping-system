#include <bluefruit.h>
#include <Arduino.h>
#include <Adafruit_TinyUSB.h> // for Serial

// LED
const int ledPin = LED_RED;
int ledState = LOW;
unsigned long previousMillis = 0;

// Parameters
const int frequency = 2; // Hz
const int sampling_frequency = 250; // Hz
const int bit_depth = 8;
int levels = pow(2, bit_depth) - 1;
int channels = 48;

BLEClientUart clientUart; // bleuart client
BLEClientBas  clientBas;  // battery service client
BLEClientDis  clientDis;  // device information service client

const int bufferSize = 240;
uint8_t dataBuffer[bufferSize];
unsigned long previousMillis = 0;
unsigned long currentMillis = 0;

void setup()
{
  Serial.begin(115200);
  while ( !Serial ) delay(10);   // for nrf52840 with native usb

  Serial.println("Bluefruit52 ECG Client");
  Serial.println("-----------------------------------\n");

  // Config the connection with maximum bandwidth 
  // more SRAM required by SoftDevice
  // Note: All config***() function must be called before begin()
  Bluefruit.configCentralBandwidth(BANDWIDTH_MAX); 
  
  // Initialize Bluefruit with maximum connections as Peripheral = 0, Central = 1
  // SRAM usage required by SoftDevice will increase dramatically with number of connections
  Bluefruit.begin(0, 1);
  
  Bluefruit.setName("Bluefruit52 Central");

  // Init BLE Central Battery Service
  clientBas.begin();

  // Init BLE Central Device Information Service
  clientDis.begin();

  // Init BLE Central Uart Serivce
  clientUart.begin();
  clientUart.setRxCallback(bleuart_rx_callback);  

  // Increase Blink rate to different from PrPh advertising mode
  Bluefruit.setConnLedInterval(250);

  // Callbacks for Central
  Bluefruit.Central.setConnectCallback(connect_callback);
  Bluefruit.Central.setDisconnectCallback(disconnect_callback);

  /* Start Central Scanning
   * - Enable auto scan if disconnected
   * - Interval = 100 ms, window = 80 ms
   * - Don't use active scan
   * - Start(timeout) with timeout = 0 will scan forever (until connected)
   */
  Bluefruit.Scanner.setRxCallback(scan_callback);
  Bluefruit.Scanner.restartOnDisconnect(true);
  Bluefruit.Scanner.setInterval(160, 80); // in unit of 0.625 ms
  Bluefruit.Scanner.useActiveScan(false);
  Bluefruit.Scanner.start(0);                   // // 0 = Don't stop scanning after n seconds
}

/**
 * Callback invoked when scanner pick up an advertising data
 * @param report Structural advertising data
 */
void scan_callback(ble_gap_evt_adv_report_t* report)
{
  // Check if advertising contain BleUart service
  if ( Bluefruit.Scanner.checkReportForService(report, clientUart) )
  {
    Serial.print("BLE UART service detected. Connecting ... ");

    // Connect to device with bleuart service in advertising
    Bluefruit.Central.connect(report);
  }else
  {      
    // For Softdevice v6: after received a report, scanner will be paused
    // We need to call Scanner resume() to continue scanning
    Bluefruit.Scanner.resume();
  }
}

/**
 * Callback invoked when an connection is established
 * @param conn_handle
 */
void connect_callback(uint16_t conn_handle)
{
  Serial.println("Connected");

  Serial.print("Dicovering Device Information ... ");
  if ( clientDis.discover(conn_handle) )
  {
    Serial.println("Found it");
    char buffer[32+1];
    
    // read and print out Manufacturer
    memset(buffer, 0, sizeof(buffer));
    if ( clientDis.getManufacturer(buffer, sizeof(buffer)) )
    {
      Serial.print("Manufacturer: ");
      Serial.println(buffer);
    }

    // read and print out Model Number
    memset(buffer, 0, sizeof(buffer));
    if ( clientDis.getModel(buffer, sizeof(buffer)) )
    {
      Serial.print("Model: ");
      Serial.println(buffer);
    }

    Serial.println();
  }else
  {
    Serial.println("Found NONE");
  }

  Serial.print("Dicovering Battery ... ");
  if ( clientBas.discover(conn_handle) )
  {
    Serial.println("Found it");
    Serial.print("Battery level: ");
    Serial.print(clientBas.read());
    Serial.println("%");
  }else
  {
    Serial.println("Found NONE");
  }

  Serial.print("Discovering BLE Uart Service ... ");
  if ( clientUart.discover(conn_handle) )
  {
    Serial.println("Found it");

    Serial.println("Enable TXD's notify");
    clientUart.enableTXD();

    Serial.println("Ready to receive from peripheral");
  }else
  {
    Serial.println("Found NONE");
    
    // disconnect since we couldn't find bleuart service
    Bluefruit.disconnect(conn_handle);
  }  
}

/**
 * Callback invoked when a connection is dropped
 * @param conn_handle
 * @param reason is a BLE_HCI_STATUS_CODE which can be found in ble_hci.h
 */
void disconnect_callback(uint16_t conn_handle, uint8_t reason)
{
  (void) conn_handle;
  (void) reason;
  
  Serial.print("Disconnected, reason = 0x"); Serial.println(reason, HEX);
}

/**
 * Callback invoked when uart received data
 * @param uart_svc Reference object to the service where the data 
 * arrived. In this example it is clientUart
 */
void bleuart_rx_callback(BLEClientUart& uart_svc)
{
  while ( uart_svc.available() )
  {
    // currentMillis = millis();
    uart_svc.read(dataBuffer, bufferSize);
    for (int i = 0; i < bufferSize; i++) {
        if (i % channels == 0) {
          Serial.println();
          delay(1000/sampling_frequency);
        }
      Serial.write(dataBuffer[i]);
      }
    // Serial.println((bufferSize*1000)/(currentMillis - previousMillis));
    // previousMillis = currentMillis;
  }
}

void loop()
{
  if ( Bluefruit.Central.connected() )
  {
    // Not discovered yet
    if ( clientUart.discovered() )
    {
      blinkLED();
    }
    
  }
}

void blinkLED()
{
  // Blink every 1 second
  if ( (millis() - previousMillis) > 1000 )
  {
    previousMillis = millis();
    Bluefruit.Central.ledToggle();
  }
}