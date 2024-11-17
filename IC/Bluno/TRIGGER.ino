#include <AceCRC.h>
#include <Arduino.h>
using namespace ace_crc::crc16modbus_byte;
#if !defined(ARDUINO_ESP32C3_DEV) // This is due to a bug in RISC-V compiler, which requires unused function sections :-(.
#define DISABLE_CODE_FOR_RECEIVER // Disables static receiver code like receive timer ISR handler and static IRReceiver and irparams data. Saves 450 bytes program memory and 269 bytes RAM if receiving functions are not required.
#endif

#include "PinDefinitionsAndMore.h"
#include <IRremote.hpp>

#define IR_T_PIN 2
#define JOYSTICK_PIN A3

// IRremote commands
uint8_t sCommand = 0x34;
uint8_t sRepeats = 0;

//////////////////////////////////////////
// 7-SEGMENT VARIABLES & FUNCTIONS
//////////////////////////////////////////
#include <ShiftRegister74HC595.h>
#define SDI 2
#define SCLK 4
#define LOAD 5
#define DIGITS 2
unsigned long delaytime = 5000; // Always wait a bit between updates of the display
int value, digit1, digit2;

// Create shift register object (number of shift registers, data pin, clock pin, latch pin)
ShiftRegister74HC595 sr(DIGITS, SDI, SCLK, LOAD);

uint8_t digits[] = {
    B11000000, // 0
    B11111001, // 1
    B10100100, // 2
    B10110000, // 3
    B10011001, // 4
    B10010010, // 5
    B10000010, // 6
    B11111000, // 7
    B10000000, // 8
    B10010000  // 9
};

// """
// two sequence numbers - incoming and outgoing - when handshake reset both to 0
//   main packet - to send - use outgoing sequence number
//   ack packet - to send - use incoming sequence number
// """
//////////////////////////////////////////
/// THIS IS THE CODE FOR PLAYER 1, BEETLE 1 - HAND //
//////////////////////////////////////////
int8_t device_id = 0x01;
const uint16_t gHandshakeTimeout = 900;
const uint16_t gPacketTimeout = 500;
const int8_t gPacketSize = 20;
volatile uint8_t gBulletCount = 6; // amount of ammo remaining
volatile uint8_t gTriggerCount = 0; // number of times the trigger has been pressed
uint8_t gLaptopSequenceNumber = 0;
uint8_t gBlunoSequenceNumber = 0;
unsigned long prev_time = millis();

//////////////////////////////////////////
// PACKET TYPES - FROM ARDUINO TO LAPTOP
//////////////////////////////////////////
struct SEND_ACK {
  char ack_packet_header = 'A';
  uint8_t id = device_id;
  uint8_t sequence_number = gLaptopSequenceNumber; // USE THE NUMBER THAT WAS RECEIVED !!! TO IMPLEMENT
  char reply = 'A'; // EDIT
  char padding_array[14] = "aaaaaaaaaaaaa";
};


struct SEND_TRIGGER { 
  char trigger_packet_header = 'T';
  uint8_t id = device_id;
  uint8_t sequence_number = gBlunoSequenceNumber; // EDIT
  char padding_array[15] = "aaaaaaaaaaaaaa";
};


//////////////////////////////////////////
// PACKET TYPES - FROM LAPTOP TO ARDUINO
//////////////////////////////////////////
struct REC_HANDSHAKE {
  char handshake_packet_header;
  uint8_t id;
  uint8_t sequence_number;
  char padding[15];
};

struct REC_ACK {
  char ack_packet_header;
  uint8_t id;
  uint8_t sequence_number;
  char ack_action;
  char padding_array[14] = "aaaaaaaaaaaaa";
};


//////////////////////////////////////////
// Main program functions
//////////////////////////////////////////
// This function creates and sends ACK with the current global sequence number
void CreateAndSendACK() {
  SEND_ACK send_ack;
  uint8_t packet[20];
  memcpy(packet, &send_ack, sizeof(SEND_ACK));
  crc_t crc = crc_calculate(packet, 18);
  packet[18] = (crc >> 8) & 0xFF;  // Upper byte of CRC
  packet[19] = crc & 0xFF;  // Lower byte of CRC
  Serial.write(packet, 20);
}

// This function handles the case where a 'H' packet header is received in the infinite loop - either by quickListen or fullListen
// This indicates that the bluno is still running but has disconnected from the laptop (out of range or data corruption over multiple packets)
void HandleReconnectionHandshake(char receivedPacket[20]) {
  char receivedChars[gPacketSize]; // create local buffer
  boolean isFullSecondPacketReceived = false;
  boolean isReconnectHandshakeComplete = false;

  // handshake packet is already in buffer and crc has been checked
  gLaptopSequenceNumber = receivedPacket[2]; // reset sequence numbers
  gBlunoSequenceNumber = receivedPacket[2];
  // send out ack with new seq num and wait for ack from laptop
  CreateAndSendACK();
  unsigned long start = millis(); // start timer to wait for reply
  while (!isReconnectHandshakeComplete) {
    while (millis() - start < gHandshakeTimeout && !isFullSecondPacketReceived) {
      if (Serial.available() >= 20) {
        for (int i = 0; i < 20; i++) {
          receivedChars[i] = Serial.read();
        }
        isFullSecondPacketReceived = true;
      }
    } 
    // If full packet not received within timeout, resend ack
    if (!isFullSecondPacketReceived) {
      CreateAndSendACK();
      start = millis(); // reset the timer
    }
    // if full packet received, calculate crc and ensure that packet header and sequence number match
    if (isFullSecondPacketReceived) {
      boolean isCRCCorrect = checkReceivedCRC(receivedChars);
      boolean isPacketHeaderCorrect = (receivedChars[0] == 'A');
      boolean isSequenceNumberCorrect = ((uint8_t)receivedChars[2] == gLaptopSequenceNumber);
      if (isPacketHeaderCorrect && isCRCCorrect && isSequenceNumberCorrect) {
        isReconnectHandshakeComplete = true; // handshake complete, move to loop
        gTriggerCount = 0; // reset trigger count after handshake received
        gBlunoSequenceNumber += 1; // increment sequence numbers to 1 after handshake
      } else {
        isFullSecondPacketReceived = false; // wait for timeout before resending ack, if new packet received don't resend ack yet
      }
    }
  }
}


// Listen to serial after sending a packet through reliable comms
// return true if full packet is received within gPacketTimout and has a correct CRC
// return false otherwise
boolean isProperPacketReturned(char receivedPacket[20]) {
  unsigned long start = millis(); // counter for timeout
  boolean isFullPacketReceived = false;

  while (millis() - start < gPacketTimeout && !isFullPacketReceived) { // listen till the first full packet before timeout
    if (Serial.available() >= 20) {
      for (int i = 0; i < 20; i++) {
        receivedPacket[i] = Serial.read();
      }
      isFullPacketReceived = true;
    }
  }
  // If full packet was received, return if CRC is correct
  // otherwise return false
  if (isFullPacketReceived) {
    boolean isCRCCorrect = checkReceivedCRC(receivedPacket);
    return isCRCCorrect;
  } else {
    return false; // full packet was not received
  }
}


// This function is called after a packet has been sent
// For reliable protocol: once a packet has been sent, listen till an ack with the same sequence number arrives
// If no packet arrives within timeout or wrong CRC received, resend packet
// If handshake arrives, handle handshake and resend packet with new sequence number
// If ack arrives, and seq number is incorrect, exit the function. Else, wait for timeout before resending packet.
void handleTransmissionReply(uint8_t packet[20]) {
  char receivedChars[gPacketSize]; // local buffer for incoming data

  while (1) {
    // If timeout or wrong crc, resend packet and wait for ack again (reset timer)
    if (!isProperPacketReturned(receivedChars)) {
      Serial.write(packet, 20); // send packet to relay laptop
      continue;
    }
    // Packet received is a full 20 bytes within the timeout with correct crc
    // perform next action based on packet header
    char packetHeader = receivedChars[0];
    if (packetHeader == 'H') { // laptop sent a reinitiate handshake command, handle the handshake and resend packet
      HandleReconnectionHandshake(receivedChars);
      // packet[2] = gBlunoSequenceNumber; // update the sequence number of the packet before sending the data
      // crc_t crc = crc_calculate(packet, 18); // update crc of packet as sequence num has changed
      // packet[18] = (crc >> 8) & 0xFF;  // Upper byte of CRC
      // packet[19] = crc & 0xFF;  // Lower byte of CRC
      // Serial.write(packet, 20); // send packet with new sequence number to relay laptop
      // continue; // wait for ack for the packet that was just sent
      break; // don't resend packet after handshake
    } else if (packetHeader == 'A') { // if ack received, check if sequence number is correct
      uint8_t receivedSeqNum = (uint8_t)receivedChars[2]; // fetch sequence number from received ack
      if (receivedSeqNum == gBlunoSequenceNumber) { // successful transmission of packet, now: update local state
        gBulletCount = (gBulletCount == 0)? 0 : gBulletCount-1;
        gTriggerCount = (gTriggerCount == 0)? 0 : gTriggerCount-1;
        gBlunoSequenceNumber = (gBlunoSequenceNumber == 255)? 1 : gBlunoSequenceNumber+1; // increment sequence number after successful transmission
        break; // sequence number is correct, transmission successful
      }
      // if sequence number does not match, discard the packet, and check next packet in the buffer
    } else if (packetHeader == 'B') { // If update packet arrives, update data, send ack and resend packet
      uint8_t receivedSeqNum = (uint8_t)receivedChars[2];
      boolean isNewPacket = isIncomingPacketNew(receivedSeqNum);
      if (isNewPacket) { // update state
        gBulletCount = (uint8_t)receivedChars[3];
      }
      CreateAndSendACK();
    }
  }
}

// Perform a quick listen to serial during every loop for 30 ms
// Perform handshake or bullet update if relay laptop sends corresponding packet
// Don't need to listen for ack as handleTransmissionReply waits for ack after sending packet
void quickListen() {
  char receivedChars[gPacketSize];
  boolean isFullPacketReceived = false;
  unsigned long start = millis();
  // delay for 30 ms, if there is a packet in serial buffer, read it and set a flag
  while (millis() - start < 2) {
    if (Serial.available() >= 20  && !isFullPacketReceived) {
      for (int i = 0; i < 20; i++) {
        receivedChars[i] = Serial.read();
      }
      isFullPacketReceived = true;
    }
  }
  // after 30 ms, check the flag, if flag has been set, process the data
  if (isFullPacketReceived) {
    boolean isCRCCorrect = checkReceivedCRC(receivedChars);
    if (isCRCCorrect) {
      char packetHeader = receivedChars[0];
      if (packetHeader == 'H') { // laptop sent a reinitiate handshake command, handle the handshake and resend packet
        HandleReconnectionHandshake(receivedChars);
      } else if (packetHeader == 'B') { // laptop sent bullet update packet
        uint8_t receivedSeqNum = (uint8_t)receivedChars[2];
        boolean isNewPacket = isIncomingPacketNew(receivedSeqNum);
        if (isNewPacket) { // update state
          gBulletCount = (uint8_t)receivedChars[3];
        }
        CreateAndSendACK(); // regardless of whether update packet was new or duplicate, send ack with current laptop seq num
      }
    }
  }
}

// This function returns true if a packet received is new and false otherwise
// Laptop sequence number is only incremented if a packet received is new
// It is called when the packet received is an update packet
boolean isIncomingPacketNew(uint8_t receivedSeqNum) {
  if (gLaptopSequenceNumber < 255) {
    if (gLaptopSequenceNumber + 1 == receivedSeqNum) {
      gLaptopSequenceNumber += 1;
      return true;
    }
  } else { // gLaptopSequenceNumber == 255
    if (receivedSeqNum == 1) {
      gLaptopSequenceNumber = 1;
      return true;
    }
  }
  return false; // receivedSeqNum is not +1 of gLaptopSequenceNumber (including overflow case)
}

boolean checkReceivedCRC(char receivedPacket[20]) {
  crc_t calculatedCRC = crc_calculate(receivedPacket, 18);
  uint16_t receivedCRC = (uint8_t)receivedPacket[18] * 256 + (uint8_t)receivedPacket[19];
  boolean isCRCCorrect = (calculatedCRC == receivedCRC);
  return isCRCCorrect;
}

  // 3 WAY HANDSHAKE PROTOCOL
void HandleInitialHandshake() {
  char receivedChars[gPacketSize]; // create local buffer
  unsigned long static start = millis();
  boolean isHandshakePacketReceived = false;
  boolean isFirstFullPacketReceived = false;
  boolean isACKPacketReceived = false;
  boolean isSecondFullPacketReceived = false;

  // Wait till a full packet arrives: If there are at least 20 characters in the buffer and
  // a full packet has not been received, read the first 20 chars and set the flag to indicate 
  // that a full packet has been received
  while (!isHandshakePacketReceived) {
    if (Serial.available() >= 20 && !isFirstFullPacketReceived) {
      for (int i = 0; i < 20; i++) {
        receivedChars[i] = Serial.read();
      }
      isFirstFullPacketReceived = true;
    }
    // If CRC and packet header are correct: send ack, else: wait till another packet arrives and repeat checks
    if (isFirstFullPacketReceived) {
      boolean isCRCCorrect = checkReceivedCRC(receivedChars);
      boolean isPacketHeaderH = (receivedChars[0] == 'H');
      if (isCRCCorrect and isPacketHeaderH) {
        gLaptopSequenceNumber = (uint8_t)receivedChars[2]; // fetch and update sequence number from handshake packet
        gBlunoSequenceNumber = (uint8_t)receivedChars[2];
        CreateAndSendACK();
        isHandshakePacketReceived = true; // handshake received, ack sent, proceed to wait for incoming ack
        start = millis(); // start the timer to trigger retransmit ack
      } else {
        isFirstFullPacketReceived = false; // reset flag to read the next packet
      }
    }
  }
  
  // Wait for ack from the laptop. If there is no ack received within the timeout, resend the ack
  // and wait for the ack packet. If there is an incorrect packet received, 
  while (!isACKPacketReceived && isHandshakePacketReceived) {
    while (millis() - start < gHandshakeTimeout && !isSecondFullPacketReceived) {
      if (Serial.available() >= 20) {
        for (int i = 0; i < 20; i++) {
          receivedChars[i] = Serial.read();
        }
        isSecondFullPacketReceived = true;
      }
    }
    // If full packet not received within timeout, proceed to resend ack and wait for the next packet
    if (!isSecondFullPacketReceived) {
      CreateAndSendACK();
      start = millis(); // restart the timer to trigger retransmit
      continue;
    }
    // If full packet received within timeout, ensure that CRC, packet header and seq number are correct
    if (isSecondFullPacketReceived) {
      boolean isCRCCorrect = checkReceivedCRC(receivedChars);
      boolean isPacketHeaderA = (receivedChars[0] == 'A');
      boolean isSeqNumberCorrect = ((uint8_t)receivedChars[2] == gLaptopSequenceNumber);
      if (isCRCCorrect and isPacketHeaderA and isSeqNumberCorrect) {
        gBlunoSequenceNumber += 1; // increment sequence number so that next packet sent will not have seq num of 0
        isACKPacketReceived = true; // set flag to exit while loop - handshake complete
        gTriggerCount = 0; // reset trigger count
      } else {
        isSecondFullPacketReceived = false; // reset flag to read the next packet
      }
    }
  }
}

void onTrigger(){
  int joystick_adc_val;
  float joystick_volt;
  
  joystick_adc_val = analogRead(JOYSTICK_PIN);
  joystick_volt = ((joystick_adc_val * 5.0) / 1023); // convert digital value to volts

  // displayNumber(gBulletCount);
  if ((joystick_volt >= 4.5 || joystick_volt <= 0.5) && millis() - prev_time > 400) {
    IrSender.sendNEC(0x00, sCommand, sRepeats);
    gTriggerCount += 1;
    prev_time = millis();
  }
}

void showNumber(int num){
    digit2 = num % 10;
    digit1 = (num / 10) % 10;
    // Send them to 7 segment displays
    uint8_t numberToPrint[] = {digits[digit2], digits[digit1]};
    sr.setAll(numberToPrint);
}

void setup() {
  Serial.begin(115200);
  HandleInitialHandshake();
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(JOYSTICK_PIN, INPUT);
  IrSender.begin();
  disableLEDFeedback();
}

void loop() {
  // RELIABLE COMMS
  if (gTriggerCount > 0) {
    uint8_t packet[20];
    SEND_TRIGGER send_trigger;
    // send_trigger.id = gBulletCount;
    memcpy(packet, &send_trigger, sizeof(SEND_TRIGGER));
    crc_t crc = crc_calculate(packet, 18);
    packet[18] = (crc >> 8) & 0xFF;  // Upper byte of CRC
    packet[19] = crc & 0xFF;  // Lower byte of CRC
    Serial.write(packet, 20);
    handleTransmissionReply(packet);
  }
  quickListen(); // 30ms delay
  onTrigger();
  showNumber(gBulletCount);
}
