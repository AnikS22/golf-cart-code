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

#include <ARD1939.h>
#include <LiquidCrystal.h>

ARD1939 j1939;

int nCounter = 0;

bool autonomous_mode;
int led = 13;  // for debug blinking

// initialize the library with the numbers of the interface pins
LiquidCrystal lcd(22,24,26,28,30,32);

// ------------------------------------------------------------------------
//  Setup routine runs on power-up or reset
// ------------------------------------------------------------------------
void setup()
{
    // Set the serial interface baud rate
    Serial.begin(9600);
    
    // Set up the LCD’s number of columns and rows:
    lcd.begin(16,2);
    // Print a message to the LCD.
    lcd.print("BrakeDuino, v0.1");
    lcd.setCursor(0,1);
    lcd.print(" Ser RxD: x");
    
    
    // Initialize the J1939 protocol including CAN settings
    if(j1939.Init(SYSTEM_TIME) == 0)
        Serial.print("CAN Controller Init OK.\n\r\n\r");
    else
        Serial.print("CAN Controller Init Failed.\n\r");
    
    // Set the preferred address and address range
    j1939.SetPreferredAddress(SA_PREFERRED);
    j1939.SetAddressRange(ADDRESSRANGEBOTTOM, ADDRESSRANGETOP);
    
    // Set the message filter
    //j1939.SetMessageFilter(59999);
    
}// end setup

// ------------------------------------------------------------------------
// Main Loop - Arduino Entry Point
// ------------------------------------------------------------------------
void loop()
{
    // J1939 Variables
    byte nMsgId;
    byte nDestAddr;
    byte nSrcAddr;
    byte nPriority;
    byte nJ1939Status;
    long lPGN;
    
    byte nData[8];
    int nDataLen;
    int nMsgLen;
    
    byte pMsg[J1939_MSGLEN];
    char sString[80];
    
    // Variables for proof of concept tests
    byte clutchOn[] = {15, 106, 196, 137, 0, 0, 0, 0};
    
    // Establish the timer base in units of milliseconds
    delay(SYSTEM_TIME);
    
    // Call the J1939 protocol stack
    nJ1939Status = j1939.Operate(&nMsgId, &lPGN, &pMsg[0], &nMsgLen, &nDestAddr, &nSrcAddr, &nPriority);
    
    if(Serial.available()){         //From RPi to Arduino
        autonomous_mode = Serial.read();
        
        // just got a new byte, if the value is 0, we are in Manual
        //   Mode (local mode), deposit the value '0' into Byte D0
        //  (Steering Map) of the outbound CAN packets
        if (autonomous_mode == true) {
            
            // BAM - Send out a periodic message with a length of more than 8 bytes
            if(nJ1939Status == NORMALDATATRAFFIC)
            {
                nCounter++;
                
                if(nCounter == (int)(5/SYSTEM_TIME))
                {
                    nSrcAddr = j1939.GetSourceAddress();
                    j1939.Transmit(0,65280,0,255,clutchOn, 8);
                    //j1939.Transmit(0,65280,0,255,report, 8);
                    nCounter = 0;
                }// end if
            }
        }
    }// end if
    
    
    // Check for reception of PGNs for our ECU/CA
    if(nMsgId == J1939_MSG_APP)
    {
        // Check J1939 protocol status
        switch(nJ1939Status)
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
    
    //    // set the cursor to column 0, line 1
    //    // (note: line 1 is the second row, since counting begins with 0):
    //    lcd.setCursor(10, 1);
    //    // print the number of seconds since reset:
    //    lcd.print(millis()/1000);
    
    // output steering angle to LCD
    //lcd.setCursor(10,1);
    //lcd.print(autonomous_mode, DEC);
    
}// end loop

