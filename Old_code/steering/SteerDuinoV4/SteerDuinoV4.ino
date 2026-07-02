#include <mcp_can.h>
#include <mcp_can_dfs.h>
#include <LiquidCrystal.h>

// Define CAN bus pin and id
// const int CAN_CS_PIN = 9;
const int CAN_BUS_ID = 0x298;

// // Define LCD pins
const int LCD_RS = A0;
const int LCD_EN = A1;
const int LCD_D4 = A2;
const int LCD_D5 = A3;
const int LCD_D6 = A4;
const int LCD_D7 = A5;

// Initialize CAN bus and LCD objects
// MCP_CAN CAN(CAN_CS_PIN);
LiquidCrystal lcd(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7);
// LiquidCrystal lcd(A0,A1,A2,A3,A4,A5);

void setup() {
  Serial.begin(9600);
  lcd.begin(16, 2);
  lcd.setCursor(0,0);
  lcd.print("Serial Data: ");
}

void displayCANMessage(unsigned char data[8], String mode) {
  Serial.print("CAN TX - ID: ");
  Serial.print(CAN_BUS_ID);
  Serial.print(", Data: 8 ");
  for(int i = 0; i < 8; i++) {
    Serial.print(data[i], DEC);
    Serial.print(" ");
  }
  Serial.println("");

  lcd.setCursor(0,1);
  lcd.print(data[1]);
}


// Function to set steering mode to manual
void setManualMode() {
  unsigned char manualModeData[8] = {0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
  // CAN.sendMsgBuf(CAN_BUS_ID, 0, 8, manualModeData);
  displayCANMessage(manualModeData, "Manual Mode");
}

// Function to set steering mode to joystick
void setJoystickMode(unsigned char joystickData) {
  unsigned char joystickModeData[8] = {0x01, joystickData, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
  // CAN.sendMsgBuf(CAN_BUS_ID, 0, 8, joystickModeData);
  displayCANMessage(joystickModeData, "Autonomous Mode");
}

void loop() {
  if (Serial.available() > 0) {
    // Read serial data as a character and convert it to an integer
    char serialData = Serial.read();
    int decimalData;

    // Check if the character is a digit
    if (isdigit(serialData)) {
      decimalData = serialData - '0'; // Convert ASCII value to integer
    } else {
      Serial.println("Invalid input");
      return;
    }

    Serial.print("Received: ");
    Serial.print(decimalData);
    Serial.print(" -> ");

    if (decimalData == 0) {
      Serial.println("Manual Mode");
      setManualMode();
    } else {
      Serial.println("Autonomous Mode");
      setJoystickMode(decimalData);
    }

  }
  delay(100);
}


// 07:23:53.311 -> 
298
07:25:41.758 -> Received: 0 -> Manual Mode
07:25:41.791 -> CAN TX - ID: 298, Data: 8 0 128 0 0 0 0 0 0 
07:25:45.457 -> Received: 1 -> A298nomous Mode
07:25:45.489 -> CAN TX - ID: 298, Data: 8 1 1 0 0 0 0 0 0 
07:25:45.587 -> Received: 2 -> A298nomous Mode
07:25:45.619 -> CAN TX - ID: 298, Data: 8 1 2 0 0 0 0 0 0 
07:25:45.717 -> Received: 8 -> A298nomous Mode
07:25:45.750 -> CAN TX - ID: 298, Data: 8 1 8 0 0 0 0 0 0 
