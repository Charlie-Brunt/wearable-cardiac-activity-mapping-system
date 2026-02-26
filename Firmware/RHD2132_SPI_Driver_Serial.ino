/*
  RHD2132 SPI driver for Arduino (Seeed XIAO nRF52840)

  - Implements RHD2000 command format and pipelined behavior
  - Uses Arduino SPI library (works with Arduino-core nRF52840)
  - Configure CS_PIN and SPI_FREQUENCY below
  - Author: ChatGPT (adapted to your provided datasheet excerpts)
*/

#include <SPI.h>
#include <Adafruit_TinyUSB.h>

// === User configuration ===
// Choose the chip-select pin you wired to the RHD2132 CS (active LOW)
#define CS_PIN 7
#define SPI_FREQUENCY 5000000UL // 5MHz / maximum 25MHz SCLK frequency

// Parameters
int sampling_frequency = 50;
int bit_resolution = 16;
int channels = 1;
const int led_interval = 500;
const int ledPin = LED_RED;
unsigned long previousMillis = 0;

// SPI mode and bit order (datasheet implies MSB first and typical SPI mode 0)
const uint8_t SPI_MODE = SPI_MODE0;
const BitOrder SPI_ORDER = MSBFIRST;

// === Command opcodes (bit patterns as per datasheet) ===
// We'll construct 16-bit words per command in functions.

class RHD2132 {
public:
  RHD2132(uint8_t csPin = CS_PIN, uint32_t freq = SPI_FREQUENCY)
    : _csPin(csPin), _spiFreq(freq) {}

  void begin() {
    pinMode(_csPin, OUTPUT);
    digitalWrite(_csPin, HIGH); // inactive
    SPI.begin();
    delay(100);
  }

  // Send an arbitrary 16-bit command (MSB first). Returns the 16-bit result
  // that the chip shifts out in response to this command. Remember: that
  // result is the *pipelined* result for a command sent *two commands earlier*.
  uint16_t sendCommand16(uint16_t cmd) {
    // Each command must be framed by CS falling edge -> SCLK -> CS rising edge.
    SPI.beginTransaction(SPISettings(_spiFreq, SPI_ORDER, SPI_MODE));
    digitalWrite(_csPin, LOW);

    // Send MSB then LSB. Use SPI.transfer(byte).
    uint8_t msb = (cmd >> 8) & 0xFF;
    uint8_t lsb = cmd & 0xFF;

    uint8_t r1 = SPI.transfer(msb);
    uint8_t r2 = SPI.transfer(lsb);

    digitalWrite(_csPin, HIGH);
    delayMicroseconds(1);
    SPI.endTransaction();

    uint16_t resp = (uint16_t(r1) << 8) | uint16_t(r2);
    return resp;
  }

  // Send a "NOP" command (all zeros). Useful to clock out a pending result.
  // Returns the 16-bit response (which will be the result of the command
  // issued two commands previously).
  uint16_t sendNOP() {
    return sendCommand16(0x0000);
  }

  // === Register access ===
  // Write 8-bit data to register R (0..63).
  // Because of pipelining, the echo/confirmation for WRITE appears two commands later.
  // This function sends WRITE then two NOPs and returns the 16-bit response of the WRITE (from the last NOP).
  // The lower byte of that response should contain the echoed D; the upper byte should be 0xFF per datasheet.
  uint16_t writeRegister(uint8_t reg, uint8_t data) {
    uint16_t cmd = 0;
    // WRITE: bits 15..0 = 0b10 R[5..0] D[7..0]
    cmd = (0x2 << 14) | ((uint16_t)(reg & 0x3F) << 8) | data;
    // Send WRITE (this will not return the write result yet)
    sendCommand16(cmd);
    // Send two NOPs to clock out the result
    sendNOP();
    uint16_t result = sendNOP();
    return result;
  }

  // Read register R (0..63).
  // Send READ command, then two NOPs; the final NOP returns the register value in lower byte.
  uint8_t readRegister(uint8_t reg) {
    uint16_t cmd = 0;
    // READ: bits 15..0 = 0b11 R[5..0] 00000000
    cmd = (0x3 << 14) | ((uint16_t)(reg & 0x3F) << 8);
    sendCommand16(cmd);
    sendNOP();
    uint16_t result = sendNOP();
    uint8_t data = result & 0xFF;
    return data;
  }

  // === ADC conversion ===
  // Request an ADC conversion on channel C (0..63). If resetDSP==true, sets H bit (lsb) to 1
  // The conversion result A is returned by the chip two commands later.
  // This function sends CONVERT(C), then two NOPs, and returns the signed 16-bit result.
  // If chip is in unsigned mode, caller can interpret differently; by default we return raw uint16_t cast to int16_t.
  int16_t convertChannel(uint8_t channel, bool resetDSP = false) {
    // Build CONVERT(C) command:
    // Bits pattern: 00 C[5..0] 0000000 H
    // Where bit 0 is H (LSB), bits 15-14 are 00.
    uint16_t cmd = 0;
    uint16_t c6 = uint16_t(channel & 0x3F);
    // cmd = (c6 << 7); // places C[5..0] into bits 13..8

    // more explicit:
    // cmd bits:
    // b15 b14 = 0 0
    // b13..b8 = C[5..0]
    // b7..b1 = 0
    // b0 = H
    cmd = (uint16_t)( (c6 << 8) & 0x3F00 ); // ensures C bits in bits 13..8
    if (resetDSP) cmd |= 0x0001u;

    sendCommand16(cmd);
    sendNOP();
    uint16_t resp = sendNOP(); // this contains the ADC conversion result A[15:0] per datasheet
    // Convert to signed int16 if twos complement mode is enabled in chip registers.
    // We cannot know the chip register 4 setting here; return as int16_t raw. Caller can treat as unsigned if needed.
    return (int16_t)resp;
  }

  // === CALIBRATE ===
  // Send CALIBRATE, then send 9 dummy commands as required by datasheet (chip ignores operations during calibrate).
  // Note: The nine commands following CALIBRATE are not executed by the RHD2000; they only provide clocks.
  void calibrate() {
    // CALIBRATE command pattern from datasheet: 0 1 0 1 0 1 0 1 0 0 0 0 0 0 0 0  (bits 15..0)
    uint16_t CAL = 0x5500; // binary 0101 0101 0000 0000 -> verify: 0x5500
    sendCommand16(CAL);
    // send 9 dummy commands (0x0000)
    for (int i = 0; i < 9; ++i) {
      uint16_t response = sendNOP();
      Serial.write(response);
    }
    // After calibration completes, the chip returns zeros (with MSB possibly indicating twoscomp)
  }

  // === CLEAR calibration ===
  void clearCalibration() {
    // CLEAR command pattern: 0 1 1 0 1 0 1 0 0 0 0 0 0 0 0 0 = 0x6A00
    uint16_t CLR = 0x6A00;
    sendCommand16(CLR);
    // result will come two commands later; if you want you can clock two NOPs and read.
    sendNOP();
    sendNOP(); // final response available here (ignore or inspect)
  }

  // Helper: read chip ID and verify it's RHD2132 (chip ID == 1 per datasheet)
  uint8_t readChipID() {
    return readRegister(63); // register 63 = chip ID
  }

private:
  uint8_t _csPin;
  uint32_t _spiFreq;
};


// Main program

RHD2132 rhd(CS_PIN, SPI_FREQUENCY);

void setup() {
  Serial.begin(1000000);
  while (!Serial) { /* wait for Serial */ }

  Serial.println("RHD2132 SPI driver starting...");
  delay(2000);
  rhd.begin();

  // Example: read ROM ID registers 40..44 ("INTAN")
  Serial.print("Reading company string regs 40..44: ");
  for (uint8_t r = 40; r <= 44; ++r) {
    uint8_t v = rhd.readRegister(r);
    Serial.print(v); // human readable format
  }
  Serial.println();

  // Read chip ID (register 63)
  uint16_t result = rhd.readRegister(63);
  Serial.print("Chip ID: 0x");
  Serial.println(result, HEX);
  // RHD2132 ID is 0x01.

  // Check number of amplifiers on the chip (32)
  uint8_t amplifiers = rhd.readRegister(62);
  Serial.print("No. of Amplifiers: ");
  Serial.println(amplifiers, DEC);

  // Check unipolar/bipolar mode
  uint8_t mode = rhd.readRegister(61);
  Serial.print("Amplifier mode: ");
  Serial.println(mode, DEC);
  // 1 = unipolar mode

  // Configure required ADC register defaults before calibration
  // Register 0 recommended values (from datasheet excerpts):
  // ADC reference BW [1:0] = 3 (bits D7..6), ADC comparator bias = 3, comparator select = 2 etc.
  // For demonstration, set register 4 DSPen=1 and twoscomp=1 (so results are signed two's complement).
  uint8_t reg4 = rhd.readRegister(4);
  // set twoscomp (bit D6) and DSPen (bit D4) per your need:
  // Register 4 bits: D7 weak MISO, D6 twoscomp, D4 DSPen
  // Here we set the DSPen bit (bit2) and twoscomp (bit5) as an example:
  // reg4 |= (1<<6); // twoscomp - signed two's complement representation
  reg4 |= (1<<4); // DSPen
  rhd.writeRegister(4, reg4);

  // Wait >100 us after enabling amp Vref if set it earlier (datasheet)
  delayMicroseconds(200);

  // Start calibration (must be done after configuration)
  Serial.println("Starting ADC calibration...");
  rhd.calibrate();
  Serial.println("Calibration command sent and clocks provided.");

  // Select amplifier bandwidth
  // Serial.println("Selecting amplifier bandwidth...")

  // uint8_t reg8 // upper bandwidth
  // uint8_t reg9 // upper bandwidth
  // uint8_t reg10 // upper bandwidth
  // uint8_t reg11 // upper bandwidth
  // uint8_t reg12 // lower bandwidth
  // uint8_t reg13 // lower bandwidth


  delay(1000);

  // read channel 0 ADC
  Serial.println("Requesting ADC conversion on channel 0...");
  int16_t sample = rhd.convertChannel(0, false);
  Serial.print("Channel 0 sample (raw 16-bit): ");
  Serial.println((int)sample);

  // write to register 14..17 (power bits) to enable all amps (set all bits to 1)
  for (uint8_t r = 14; r <= 17; ++r) {
    rhd.writeRegister(r, 0xFF);
  }

  Serial.println("Setup done.");
  delay(4000);
}

void loop() {
  // Simple example stream: request convert(0) each loop and print value.
  int16_t v = rhd.convertChannel(0, false);
  Serial.println((int)v);
  // Serial.write(v)
  delay(1000/sampling_frequency); // sample at 10 Hz here; set appropriate timing
  blinkLED();

  // for (uint8_t c = 0; c <=31; +=c) {
  //   int16_t v = rhd.convertChannel(c, false);
  //   Serial.write(v);
  // }
  // delay(1000/sampling_frequency);
}

void blinkLED() {
  unsigned long currentMillis = millis();  // Get the current time

  // Check if it's time to blink the LED
  if (currentMillis - previousMillis >= led_interval) {
    // Save the last time the LED blinked
    previousMillis = currentMillis;

    // If the LED is off, turn it on. If it's on, turn it off.
    digitalWrite(ledPin, !digitalRead(ledPin));
  }
}
