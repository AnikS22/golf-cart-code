// ------------------------------------------------------------------------
// ARD1939 - SAE J1939 Protocol Stack for Arduino Uno and Mega2560
// ------------------------------------------------------------------------
//
// IMPOPRTANT: Depending on the CAN shield used for this programming sample,
//             please make sure you set the proper CS pin in ARD1939.h.
//
//  This Arduino program is free software; you can redistribute it and/or
//  modify it under the terms of the GNU Lesser General Public
//  License as published by the Free Software Foundation; either
//  version 2.1 of the License, or (at your option) any later version.

//  This program is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
//  Lesser General Public License for more details.

#include <stdlib.h>
#include <inttypes.h>
#include <SPI.h>
#include "mcp_can.h"
#include "can_ext.h"

#include "ARD1939.h"
#include <LiquidCrystal.h>

ARD1939 j1939;

int nCounter = 0;

bool autonomous_mode;
int prevDemand = 0;
char brakeDemand;
char MSBArray[9];
char LSBArray[9];

String wholeBin;
long unsigned int LSB;
long unsigned int MSB;

long unsigned int byteTwo;
long unsigned int byteThree;

String triggerStatus = "NA";

int led = 13;  // for debug blinking

// initialize the library with the numbers of the interface pins
LiquidCrystal lcd(A0, A1, A2, A3, A4, A5);

// ------------------------------------------------------------------------
//  Setup routine runs on power-up or reset
// ------------------------------------------------------------------------
void setup()
{
  // Set the serial interface baud rate
  Serial.begin(9600);

  // Set up the LCD’s number of columns and rows:
  lcd.begin(16, 2);
  // Print a message to the LCD.
  lcd.print("BrakeDuino, v0.1");
  //  lcd.setCursor(0, 1);
  //  lcd.print(" Ser RxD: x");

  //   Initialize the J1939 protocol including CAN settings
  if (j1939.Init(SYSTEM_TIME) == 0)
    Serial.print("CAN Controller Init OK.\n\r\n\r");
  else
    Serial.print("CAN Controller Init Failed.\n\r");

  // Set the preferred address and address range
  j1939.SetPreferredAddress(SA_PREFERRED);
  j1939.SetAddressRange(ADDRESSRANGEBOTTOM, ADDRESSRANGETOP);

  // Set the message filter
  //j1939.SetMessageFilter(59999);

}// end setup

//********************************J1939 Functions*********************************//
// Check for reception of PGNs for our ECU/CA
void checkStatus() {
  byte nMsgId;
  byte nJ1939Status;

  if (nMsgId == J1939_MSG_APP)
  {
    // Check J1939 protocol status
    switch (nJ1939Status)
    {
      case ADDRESSCLAIM_INPROGRESS:
        Serial.print("ADDRESSCLAIM_INPROGRESS \n\r");
        break;
      case NORMALDATATRAFFIC:
        Serial.print("NORMALDATATRAFFIC \n\r");
        break;
      case ADDRESSCLAIM_FAILED:
        Serial.print("ADDRESSCLAIM_FAILED\n\r");
        break;
    }// end switch(nJ1939Status)
  }// end if
}

// BAM - Send out a periodic message with a length of more than 8 bytes
int clutchSwitch(int x) {
  byte nMsgId; byte nDestAddr; byte nSrcAddr; byte nPriority; byte nJ1939Status;
  long lPGN;
  int nDataLen; int nMsgLen;
  byte nData[8]; byte pMsg[J1939_MSGLEN];
  char sString[80];

  byte clutchOn[] = {15, 74, 196, 137, 0, 0, 0, 0};
  byte clutchOff[] = {15, 74, 208, 7, 0, 0, 0, 0};

  // Call the J1939 protocol stack
  nJ1939Status = j1939.Operate(&nMsgId, &lPGN, &pMsg[0], &nMsgLen, &nDestAddr, &nSrcAddr, &nPriority);

  if (nJ1939Status == NORMALDATATRAFFIC)
  {
    nCounter++;

    if (nCounter == (int)(5 / SYSTEM_TIME))
    {
      if (x > 50) {
        nSrcAddr = j1939.GetSourceAddress();
        j1939.Transmit(0, 65280, 0, 255, clutchOn, 8);
        nCounter = 0;
      }
      else {
        nSrcAddr = j1939.GetSourceAddress();
        j1939.Transmit(0, 65280, 0, 255, clutchOff, 8);
      }
      nCounter = 0;
    }// end if
  }

  return 0;
}

int goOut(int x) {
  byte nMsgId; byte nDestAddr; byte nSrcAddr; byte nPriority; byte nJ1939Status;
  long lPGN;
  int nDataLen; int nMsgLen;
  byte nData[8]; byte pMsg[J1939_MSGLEN];
  char sString[80];
  int prevValue;

  byte clutchOn[] = {15, 74, 196, 137, 0, 0, 0, 0};
  byte clutchOff[] = {15, 74, 208, 7, 0, 0, 0, 0};
  byte moveThree[] = {15, 74, 91, 204, 0, 0, 0, 0};
  byte moveBack[] = {15, 74, 238, 195, 0, 0, 0, 0};
  byte moveBack2[] = {15, 74, 109, 201, 0, 0, 0, 0};
  //    prevValue = x;

  // Call the J1939 protocol stack
  nJ1939Status = j1939.Operate(&nMsgId, &lPGN, &pMsg[0], &nMsgLen, &nDestAddr, &nSrcAddr, &nPriority);

  if (nJ1939Status == NORMALDATATRAFFIC)
  {
    nCounter++;

    if (nCounter == (int)(5 / SYSTEM_TIME))
    {
      switch (x)
        if (x > 100) {
          nSrcAddr = j1939.GetSourceAddress();
          j1939.Transmit(0, 65280, 0, 255, moveThree, 8);
          nCounter = 0;
          break;
        }
        else if (x < 100) {
          nSrcAddr = j1939.GetSourceAddress();
          j1939.Transmit(0, 65280, 0, 255, moveBack, 8);
          nCounter = 0;
        }
      if (x == 0) {
        nSrcAddr = j1939.GetSourceAddress();
        j1939.Transmit(0, 65280, 0, 255, clutchOff, 8);
        nCounter = 0;
      }
    }// end if
  }
  return x;
}

void goBack() {
  byte nMsgId; byte nDestAddr; byte nSrcAddr; byte nPriority; byte nJ1939Status;
  long lPGN;
  int nDataLen; int nMsgLen;
  byte nData[8]; byte pMsg[J1939_MSGLEN];
  char sString[80];

  byte braking[] = {15, 74, 193, 203, 0, 0, 0, 0};
  byte brakeLight[] = {15, 74, 105, 204, 0, 0, 0, 0};

  // Call the J1939 protocol stack
  nJ1939Status = j1939.Operate(&nMsgId, &lPGN, &pMsg[0], &nMsgLen, &nDestAddr, &nSrcAddr, &nPriority);

  if (nJ1939Status == NORMALDATATRAFFIC)
  {
    nCounter++;

    if (nCounter == (int)(5 / SYSTEM_TIME))
    {
      nSrcAddr = j1939.GetSourceAddress();
      j1939.Transmit(0, 65280, 0, 255, braking, 8);
      nCounter = 0;
    }// end if
  }
  checkStatus();
}

void gotoStock() {
  byte nMsgId; byte nDestAddr; byte nSrcAddr; byte nPriority; byte nJ1939Status;
  long lPGN;
  int nDataLen; int nMsgLen;
  byte nData[8]; byte pMsg[J1939_MSGLEN];
  char sString[80];

  byte stock[] = {15, 74, 192, 205, 0, 0, 0, 0};
  byte clutchOn[] = {15, 74, 196, 137, 0, 0, 0, 0};

  // Call the J1939 protocol stack
  nJ1939Status = j1939.Operate(&nMsgId, &lPGN, &pMsg[0], &nMsgLen, &nDestAddr, &nSrcAddr, &nPriority);

  if (nJ1939Status == NORMALDATATRAFFIC)
  {
    nCounter++;

    if (nCounter == (int)(5 / SYSTEM_TIME))
    {
      nSrcAddr = j1939.GetSourceAddress();
      //      j1939.Transmit(0, 65280, 0, 255, clutchOn, 8);
      //      delay(20);
      j1939.Transmit(0, 65280, 0, 255, stock, 8);
      nCounter = 0;
    }// end if
  }
  checkStatus();
}

void binaryToInt(unsigned int x) {
  char itoaArray[16];
  int input = x * 40;

  char indexOne;
  char indexTwo;
  itoa(input, itoaArray, 2);
  long int itoaDec = strtol(itoaArray, NULL, 2);

  //  if (input == 0) {
  //    Serial.println(x);
  //    indexOne = '0';
  //  } else if (input > 0) {
  //    indexOne == '1';
  //  }

  Serial.println(indexOne);
  //  Serial.println(String("Binary = ") + itoaArray);
  //    Serial.println(String("Array Length ") + strlen(itoaArray));
  //    Serial.println(String("Decimal = ") + strtol(itoaArray, NULL, 2));

  if (strlen(itoaArray) == 9)
  {


    MSBArray[0] = '1';//indexOne;
    MSBArray[1] = '1';//indexOne;;
    MSBArray[2] = '0';
    MSBArray[3] = '0';
    MSBArray[4] = '0';
    MSBArray[5] = '0';
    MSBArray[6] = '0';
    MSBArray[7] = itoaArray[0];

    LSBArray[0] = itoaArray[1];
    LSBArray[1] = itoaArray[2];
    LSBArray[2] = itoaArray[3];
    LSBArray[3] = itoaArray[4];
    LSBArray[4] = itoaArray[5];
    LSBArray[5] = itoaArray[6];
    LSBArray[6] = itoaArray[7];
    LSBArray[7] = itoaArray[8];

    //    Serial.println(String("Length of 1st eight = ") + strlen(MSBArray));
    //    Serial.println(String("1st 8 = ") + MSBArray);
    //    Serial.println(String("Length of 2nd eight = ") + strlen(LSBArray));
    //        Serial.println(String("2nd 8 = ") + LSBArray[0]);
  }
  else if (strlen(itoaArray) == 10)
  {
    //    if (itoaArray[2] == '0' or (itoaArray[3] == '0'))
    //    {
    //      indexOne = '1';
    //      Serial.println ("Equals 0");
    //    } else { indexOne == itoaArray[2]; }

    MSBArray[0] = '1';//indexOne;;
    MSBArray[1] = '1';//indexOne;;
    MSBArray[2] = '0';
    MSBArray[3] = '0';
    MSBArray[4] = '0';
    MSBArray[5] = '0';
    MSBArray[6] = itoaArray[0];
    MSBArray[7] = itoaArray[1];

    LSBArray[0] = itoaArray[2];
    LSBArray[1] = itoaArray[3];
    LSBArray[2] = itoaArray[4];
    LSBArray[3] = itoaArray[5];
    LSBArray[4] = itoaArray[6];
    LSBArray[5] = itoaArray[7];
    LSBArray[6] = itoaArray[8];
    LSBArray[7] = itoaArray[9];

    //    Serial.println(String("Length of 1st eight = ") + strlen(MSBArray));
    //    Serial.println(String("1st 8 = ") + MSBArray);
    //    Serial.println(String("Length of 2nd eight = ") + strlen(LSBArray));
    //        Serial.println(String("2nd 8 = ") + LSBArray);
  }
  else if (strlen(itoaArray) == 11)
  {
    MSBArray[0] = '1';//indexOne;;
    MSBArray[1] = '1';//indexOne;;
    MSBArray[2] = '0';
    MSBArray[3] = '0';
    MSBArray[4] = '0';
    MSBArray[5] = itoaArray[0];
    MSBArray[6] = itoaArray[1];
    MSBArray[7] = itoaArray[2];

    LSBArray[0] = itoaArray[3];
    LSBArray[1] = itoaArray[4];
    LSBArray[2] = itoaArray[5];
    LSBArray[3] = itoaArray[6];
    LSBArray[4] = itoaArray[7];
    LSBArray[5] = itoaArray[8];
    LSBArray[6] = itoaArray[9];
    LSBArray[7] = itoaArray[10];

    //    Serial.println(String("Length of 1st eight = ") + strlen(MSBArray));
    //    Serial.println(String("1st 8 = ") + MSBArray);
    //    Serial.println(String("Length of 2nd eight = ") + strlen(LSBArray));
    //    Serial.println(String("2nd 8 = ") + LSBArray);
  }
  else if (strlen(itoaArray) == 12)
  {
    MSBArray[0] = '1';//indexOne;;
    MSBArray[1] = '1';//indexOne;;
    MSBArray[2] = '0';
    MSBArray[3] = '0';
    MSBArray[4] = itoaArray[0];
    MSBArray[5] = itoaArray[1];
    MSBArray[6] = itoaArray[2];
    MSBArray[7] = itoaArray[3];

    LSBArray[0] = itoaArray[4];
    LSBArray[1] = itoaArray[5];
    LSBArray[2] = itoaArray[6];
    LSBArray[3] = itoaArray[7];
    LSBArray[4] = itoaArray[8];
    LSBArray[5] = itoaArray[9];
    LSBArray[6] = itoaArray[10];
    LSBArray[7] = itoaArray[11];

    //    Serial.println(String("Length of 1st eight = ") + strlen(MSBArray));
    //    Serial.println(String("1st 8 = ") + MSBArray);
    //    Serial.println(String("Length of 2nd eight = ") + strlen(LSBArray));
    //    Serial.println(String("2nd 8 = ") + LSBArray);
  }

  LSB = strtoul(LSBArray, NULL, 2);
  MSB = strtoul(MSBArray, NULL, 2);
}

void moveShaft(unsigned int inputOne, unsigned int inputTwo) {
  byte nMsgId; byte nDestAddr; byte nSrcAddr; byte nPriority; byte nJ1939Status;
  long lPGN;
  int nDataLen; int nMsgLen;
  byte nData[8]; byte pMsg[J1939_MSGLEN];
  char sString[80];

  byte clutchOn[] = {15, 74, 196, 137, 0, 0, 0, 0};
  byte clutchOff[] = {15, 74, 208, 7, 0, 0, 0, 0};
  byte moveThree[] = {15, 74, 91, 204, 0, 0, 0, 0};
  byte moveBack[] = {15, 74, 238, 195, 0, 0, 0, 0};
  byte moveBack2[] = {15, 74, 109, 201, 0, 0, 0, 0};

  byte moveBySerial[] = {15, 74, inputOne, inputTwo, 0, 0, 0, 0};

  byteTwo = inputOne;
  byteThree = inputTwo;

  // Establish the timer base in units of milliseconds
  delay(SYSTEM_TIME);

  // Call the J1939 protocol stack
  nJ1939Status = j1939.Operate(&nMsgId, &lPGN, &pMsg[0], &nMsgLen, &nDestAddr, &nSrcAddr, &nPriority);

  // Send out a periodic message with a length of more than 8 bytes | BAM Session
  if (nJ1939Status == NORMALDATATRAFFIC)
  {
    nCounter++;
    if (nCounter == (int)(5 / SYSTEM_TIME))
    {
      nSrcAddr = j1939.GetSourceAddress();
      j1939.Transmit(0, 65280, 0, 255, moveBySerial, 8);
      nCounter = 0;
    }//end if
  }// end if

  checkStatus();
}
// ------------------------------------------------------------------------
// Main Loop - Arduino Entry Point
// ------------------------------------------------------------------------
void loop()
{
  // Establish the timer base in units of milliseconds
  //    delay(SYSTEM_TIME);

  //    sendBam();
  //    checkStatus();


  //  binaryToInt(25);
  //  moveShaft(LSB, MSB);
  //    Serial.println(String("LSB: ") + LSB + String(" MSB: ") + MSB);

  if (Serial.available() > 0) {        //From RPi to Arduino
    brakeDemand = Serial.read();
    prevDemand = brakeDemand;
    binaryToInt(brakeDemand);

    if (brakeDemand == 0) {
      moveShaft(0, 0);
    } else {
      moveShaft(LSB, MSB);
    }

    //
    //    if (int(brakeDemand) > prevDemand) {
    //      triggerStatus = "Down";
    //    }
    //    else if (int(brakeDemand) < prevDemand) {
    //      triggerStatus = "Up";
    //    }
    //      Serial.println(String("PREVIOUS: ") + prevDemand);
    //      Serial.println(String("CURRENT: ") + int(brakeDemand));
    //      Serial.println(String("TRIGGER IS GOING ") + triggerStatus);

  }// end if serial available

  // output steering angle to LCD
  lcd.setCursor(0, 1);
  lcd.print(byteTwo);
  //  lcd.print(LSB);

  lcd.setCursor(6, 1);
  lcd.print(int(brakeDemand));

  lcd.setCursor(12, 1);
  lcd.print(byteThree);
  //  lcd.print(MSB);
  //  }
}// end loop
