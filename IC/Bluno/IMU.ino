#include <AceCRC.h>
using namespace ace_crc::crc16modbus_byte;
#include "I2Cdev.h"
#include "MPU6050.h"
#if I2CDEV_IMPLEMENTATION == I2CDEV_ARDUINO_WIRE
    #include "Wire.h"
#endif
//////////////////////////////////////////
/// THIS IS THE CODE FOR PLAYER 1, BEETLE 1 - HAND //
//////////////////////////////////////////
int8_t device_id = 0x01;
uint8_t gSeqNum = 0;
const uint16_t gHandshakeTimeout = 900;
const int8_t gPacketSize = 20;
// int16_t gVal = 0;

MPU6050 accelgyro;

int16_t Ax, Ay, Az;
int16_t Gx, Gy, Gz;
#define OUTPUT_READABLE_ACCELGYRO


//////////////////////////////////////////
// PACKET TYPES - FROM ARDUINO TO LAPTOP
//////////////////////////////////////////
struct SEND_ACK {
  char ack_packet_header = 'A';
  uint8_t id = device_id;
  uint8_t sequence_number = gSeqNum; // EDIT
  char reply = 'A'; // EDIT
  char padding_array[14] = "aaaaaaaaaaaaa";
};

// order will be swapped for uint16_t at python side

struct SEND_IMU { 
  char imu_packet_header = 'I';
  uint8_t id = device_id;
  uint8_t sequence_number = gSeqNum; // EDIT
  int16_t aX = -30000; // fetch
  int16_t aY = 30000; // fetch
  int16_t aZ = -1; // fetch
  int16_t gX = 1; // fetch
  int16_t gY = 0; // fetch
  int16_t gZ = -10000; // fetch
  char padding_array[3] = "aa";
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

// This function calculates the crc of an 18 byte array and appends the crc to the 19th and 20th byte (1 index)
// void AddCRCToPacket(uint8_t* packet[20]) {
//   crc_t crc = crc_calculate(packet, 18);
//   packet[18] = (crc >> 8) & 0xFF;  // Upper byte of CRC
//   packet[19] = crc & 0xFF;  // Lower byte of CRC
// }

// This function handles the case where a 'H' packet header is received in  quickListen
// This indicates that the bluno is still running but has disconnected from the laptop (out of range or data corruption over multiple packets)
void HandleReconnectionHandshake(char receivedPacket[20]) {
  char receivedChars[gPacketSize]; // create local buffer
  boolean isFullSecondPacketReceived = false;
  boolean isReconnectHandshakeComplete = false;

  // handshake packet is already in buffer and crc has been checked
  gSeqNum = receivedPacket[2]; // update global seq num obtained from packet received
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
      boolean isSequenceNumberCorrect = ((uint8_t)receivedChars[2] == gSeqNum);
      if (isPacketHeaderCorrect && isCRCCorrect && isSequenceNumberCorrect) {
        isReconnectHandshakeComplete = true; // handshake complete, move to loop
        gSeqNum++; // increment sequence number
      } else {
        isFullSecondPacketReceived = false; // wait for timeout before resending ack, if new packet received don't resend ack yet
      }
    }
  }
}


// Perform a quick listen to serial after every loop for 30 ms
// Perform handshake if relay laptop sends handshake packet
void quickListen() {
  char receivedChars[gPacketSize];
  boolean isFullPacketReceived = false;
  unsigned long start = millis();
  // delay for 30 ms, if there is a packet in serial buffer, read it and set a flag
  while (millis() - start < 30) {
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
      }
    }
  }
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
        gSeqNum = (uint8_t)receivedChars[2]; // fetch and update sequence number from handshake packet
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
      boolean isSeqNumberCorrect = ((uint8_t)receivedChars[2] == gSeqNum);
      if (isCRCCorrect and isPacketHeaderA and isSeqNumberCorrect) {
        gSeqNum += 1; // increment sequence number so that next packet sent will not have seq num of 0
        isACKPacketReceived = true; // set flag to exit while loop - handshake complete
      } else {
        isSecondFullPacketReceived = false; // reset flag to read the next packet
      }
    }
  }
}


void setup() {
  #if I2CDEV_IMPLEMENTATION == I2CDEV_ARDUINO_WIRE
    Wire.begin();
  #elif I2CDEV_IMPLEMENTATION == I2CDEV_BUILTIN_FASTWIRE
    Fastwire::setup(400, true);
  #endif
  Serial.begin(115200);
  accelgyro.initialize();
  HandleInitialHandshake();
}

void loop() {
  // UNRELIABLE COMMS
  uint8_t packet[20];
  accelgyro.getMotion6(&Ax, &Ay, &Az, &Gx, &Gy, &Gz);
  SEND_IMU send_imu;
  send_imu.aX = Ax;
  send_imu.aY = Ay;
  send_imu.aZ = Az;
  send_imu.gX = Gx;
  send_imu.gY = Gy;
  send_imu.gZ = Gz;
  memcpy(packet, &send_imu, sizeof(SEND_IMU));
  crc_t crc = crc_calculate(packet, 18);
  packet[18] = (crc >> 8) & 0xFF;  // Upper byte of CRC
  packet[19] = crc & 0xFF;  // Lower byte of CRC
  Serial.write(packet, 20); // transmit packet
  gSeqNum = (gSeqNum == 255)? 1: gSeqNum + 1; // increment sequence number after transmission
  quickListen();
  // gVal += 100;
}


