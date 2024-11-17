#include <AceCRC.h>
using namespace ace_crc::crc16modbus_byte;

#include "Arduino.h"
#include "I2Cdev.h"
#if I2CDEV_IMPLEMENTATION == I2CDEV_ARDUINO_WIRE
    #include "Wire.h"
#endif

#define DECODE_NEC
#include "PinDefinitionsAndMore.h"
#include <IRremote.h>

#define IR_RECEIVE_PIN 2

#include <LiquidCrystal_I2C.h>
#if defined(ARDUINO) && ARDUINO >= 100
#define printByte(args)  write(args);
#else
#define printByte(args)  print(args,BYTE);
#endif
int backlightState = LOW;
long previousMillis = 0;
long interval = 1000;
LiquidCrystal_I2C lcd(0x27,16,2);

uint8_t heart[5][8] = {
  {0x0,0xa,0x1f,0x1f,0xe,0x4,0x0},
  {0x0,0x0,0x10,0x10,0x0,0x0,0x0},
  {0x0,0x8,0x18,0x18,0x8,0x0,0x0},
  {0x0,0x8,0x1c,0x1c,0xc,0x4,0x0},
  {0x0,0xa,0x1e,0x1e,0xe,0x4,0x0}};

// """
// two sequence numbers - incoming and outgoing - when handshake reset both to 0
//   main packet - to send - use outgoing sequence number
//   ack packet - to send - use incoming sequence number
// """
//////////////////////////////////////////
/// THIS IS THE CODE FOR PLAYER 1, VEST //
//////////////////////////////////////////
int8_t device_id = 0x04;
const uint16_t gHandshakeTimeout = 900;
const uint16_t gPacketTimeout = 500;
const int8_t gPacketSize = 20;
volatile uint8_t gHPCount = 100; // amount of hit points remaining
volatile uint8_t gHitCount = 0; // number of times the player got shot
uint8_t gLaptopSequenceNumber = 0;
uint8_t gBlunoSequenceNumber = 0;

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


struct SEND_HIT { 
  char hit_packet_header = 'S';
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
        gHitCount = 0; // reset trigger count after handshake received
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
        gHPCount = (gHPCount == 0)? 0 : gHPCount-5;
        gHitCount = (gHitCount == 0)? 0 : gHitCount-1;
        gBlunoSequenceNumber = (gBlunoSequenceNumber == 255)? 1 : gBlunoSequenceNumber+1; // increment sequence number after successful transmission
        break; // sequence number is correct, transmission successful
      }
      // if sequence number does not match, discard the packet, and check next packet in the buffer
    } else if (packetHeader == 'X') { // If update packet arrives, update data, send ack and resend packet
      uint8_t receivedSeqNum = (uint8_t)receivedChars[2];
      boolean isNewPacket = isIncomingPacketNew(receivedSeqNum);
      if (isNewPacket) { // update state
        gHPCount = (uint8_t)receivedChars[3];
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
      } else if (packetHeader == 'X') { // laptop sent hp update packet
        uint8_t receivedSeqNum = (uint8_t)receivedChars[2];
        boolean isNewPacket = isIncomingPacketNew(receivedSeqNum);
        if (isNewPacket) { // update state
          gHPCount = (uint8_t)receivedChars[3];
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
        gHitCount = 0; // reset trigger count
      } else {
        isSecondFullPacketReceived = false; // reset flag to read the next packet
      }
    }
  }
}

void onHit() {
  if(IrReceiver.decode()) {
    IrReceiver.resume();
    if (IrReceiver.decodedIRData.command == 52) {
      gHitCount += 1;
    }
  }
}

// LCD initialisation
void screenSetup(){
  lcd.init();
  lcd.backlight();
  for(int i = 0; i < 5; i++){
    lcd.createChar(i, heart[i]);
  }
  lcd.home();
  lcd.setCursor(0, 0);
  lcd.print("Player 2");
}

// Health display functions
void healthDisplay(){
  int maxHearts = ceil(gHPCount / 10.0);
  int lastHeart = gHPCount % 10;
  // If HP is not a multiple of 10
  if(lastHeart > 0){
    for(int i = 0; i < maxHearts; i++){
    lcd.setCursor(i, 1);
    lcd.printByte(0);
    }
    lcd.setCursor(maxHearts-1, 1);
    lcd.printByte(lastHeart/2);
  }
  // If HP is a multiple of 10
  else if(lastHeart == 0){
    for(int i = 0; i < maxHearts; i++){
      lcd.setCursor(i, 1);
      lcd.printByte(0);
    }
    lcd.setCursor(maxHearts, 1);
    lcd.printByte("");
  }
}

void setup() {
  #if I2CDEV_IMPLEMENTATION == I2CDEV_ARDUINO_WIRE
    Wire.begin();
    Wire.setClock(400000); // 400kHz I2C clock. Comment this line if having compilation difficulties
  #elif I2CDEV_IMPLEMENTATION == I2CDEV_BUILTIN_FASTWIRE
    Fastwire::setup(400, true);
  #endif
  Serial.begin(115200);
  HandleInitialHandshake();
  IrReceiver.begin(IR_RECEIVE_PIN, ENABLE_LED_FEEDBACK);
  attachInterrupt(digitalPinToInterrupt(IR_RECEIVE_PIN), onHit, CHANGE);
  screenSetup();
}

void loop() {
  // RELIABLE COMMS
  if (gHitCount > 0) {
    uint8_t packet[20];
    SEND_HIT send_hit;
    memcpy(packet, &send_hit, sizeof(SEND_HIT));
    crc_t crc = crc_calculate(packet, 18);
    packet[18] = (crc >> 8) & 0xFF;  // Upper byte of CRC
    packet[19] = crc & 0xFF;  // Lower byte of CRC
    Serial.write(packet, 20);
    handleTransmissionReply(packet);
  }
  quickListen();
  healthDisplay();
}
