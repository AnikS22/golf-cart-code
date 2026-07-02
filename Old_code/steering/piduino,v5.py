#!/usr/bin/python

#PiDuino,v4 - the "restored" version of Christmas 2019,
#  renumbered for convenience, no other changes
#
#Piduino, V3 - this iteration starts with V2 working
#  correctly for wireless speed control, adds new
#  functionality to enter and leave (toggle) autonomous
#  mode on the press of LB Button or release of auto mode
#  upon any touch to LT (brakes). We normally transmit
#  steering_angle_request value but will send special
#  case of ZERO to indicate Local Mode (Manual Control)
#  with any non-zero data being interpreted as enter
#  Remote Mode (Autonomous Control).
#
# v3 - reversed the calculations of direction because
#      sensor was wired backwards


import serial
import time
import pygame

# Configuration Contants, speed_low is max steering angle
#        unshifted, speed_high is max angle shifted
speed_low  = 1000 / 10     # 5 is five degrees each side
speed_high = 1000 / 20     # when shifted, 10 is ten degrees


# setup()     // Arduin-who?

# Set up the serial port to talk to the Arduino
ser=serial.Serial("/dev/ttyACM0",9600)  #change ACM number as found from ls /dev/tty/ACM*
ser.baudrate=9600

# prepare pygame for use
pygame.init()
joystick= pygame.joystick.Joystick(0)
joystick.init()

# setup state variables
steering_shift = 0
autonomous_mode = False  # TRUE when autonomous is enabled, else FALSE
auto_button_pressed = False

while True:
    pygame.event.get()
    
    # process the stweering shift state
    if joystick.get_button(5) == 1 and steering_shift == 0 :
        print("Button Down")
        steering_shift = True
    if joystick.get_button(5) == 0 and steering_shift == 1 :
        print("Button Up")
        steering_shift = False
        
    # process the autonomous_mode state
    if joystick.get_button(4) == 1 :
        print("Auto Button Down")
        auto_button_pressed = True
        #do nothing
    if joystick.get_button(4) == 0 and auto_button_pressed == True :
        print("Auto Button Up")
        auto_button_pressed = False
        # value changes only on release
        autonomous_mode = not autonomous_mode
        print("autonomous_mode = ", autonomous_mode)
        
    # check whether brake lever is touched, also exits auto mode
    #   we are seeing 0.0 if button has not yet been touched
    joyLT = joystick.get_axis(2)  # buttom LT is axis 2
    if joyLT > -1.0 and joyLT != 0.0 and autonomous_mode == True :   
        print("Brake Lever Active ")
        autonomous_mode = False
        #print("autonomous_mode = ", autonomous_mode)
        
    # get axis value from joystick
    steering_value = joystick.get_axis(3)
    
    # convert to byte value, scale to steering range
    cooked_sv = int(1000.0 * round(steering_value,4))
    #print (cooked_sv)
    
    if steering_shift :     #shifted, more angle
     #   steering_angle = int(  )
        steering_angle_demand = int(cooked_sv / speed_high)
         
    else :                  #not shifted, less angle
        steering_angle_demand = int(cooked_sv / speed_low)
        
    #print(steering_angle_demand)
    
    # convert to 128-biased value for ECU
    if steering_angle_demand > 0 :
            output_byte = 128 + steering_angle_demand
    elif steering_angle_demand < 0 :
            output_byte = 128 - abs(steering_angle_demand)
    else :
            output_byte = 128
            

    # handle auto mode
    if (autonomous_mode == False) :
        output_byte = 0;
    print(output_byte)
    
     # send the byte value to the Arduino
#    output_byte_encoded = b'%d' % output_byte
#    print(output_byte_encoded)
    
 #   output_byte.to_bytes(1)
    ser.write(output_byte.to_bytes(1, byteorder='big'))
    
    
    # delay the loop() if needed
    time.sleep(.1)

    
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
    prevValue = x;
    
    // Call the J1939 protocol stack
    nJ1939Status = j1939.Operate(&nMsgId, &lPGN, &pMsg[0], &nMsgLen, &nDestAddr, &nSrcAddr, &nPriority);
    #//    prevValue = x;
    
    if(nJ1939Status == NORMALDATATRAFFIC)
    {
        nCounter++;
    
    if(nCounter == (int)(5/SYSTEM_TIME))
    {
        nSrcAddr = j1939.GetSourceAddress();
    #//      if (x > 150 < 250) {
        if (x > prevValue) {
        j1939.Transmit(0,65280,0,255,moveThree, 8);
        else if (x < prevValue) {
            j1939.Transmit(0,65280,0,255,moveBack, 8); }
        nCounter = 0;
        #    }// end if
        }
        return 0;
        }
        }
