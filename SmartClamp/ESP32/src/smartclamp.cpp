/*
 *    FILE: SmartClamp.cpp
 *  AUTHOR: Cristian Garcia
 *    DATE: 2019 09 08
 */

//////////////////////////////////////////////////////////////////////////////////
//
//  Definitions and Declarations
//
//////////////////////////////


#define SMARTCLAMP_VERSION  "0.14"
#include <Arduino.h>
#include <Wire.h>                                                      //Enables I2C Comms
#include <SPI.h>                                                       //Enables SPI Comms
// #include <SFE_MicroOLED.h>                                             // Include the SFE_MicroOLED library
// #include <MPU6050_tockn>                                             //MPU6050 reference library




//Serial Comms
#define SERIAL_BUFFER_LEN 128                                          // Defines Arduino buffer as 128 bytes instead of 64                                                  // Interval of sent data
char serialBuffer[SERIAL_BUFFER_LEN];
unsigned short bufferEnd = 0;
unsigned short bufferPos = 0;




// Light Detection
#define SENSOR_A_PIN  27
#define LIGHT_PIN     25
#define POT_PIN       26
#define POT_ADDR      0x00

bool lightOn = false;
bool sensor_Enable = true;
volatile unsigned long cnta = 0;
unsigned long oldcnta = 0;
float Ia = 0;                                                          // current intensity of sensor A in uW/m2
byte light_int = 128;                                                  //Changes potentiometer resistance from 10kΩ to 0Ω [0-128]
byte light_sampling = 1;



// OLED Display
// #define CS_OLED   10
// #define PIN_RESET 9                                                    // Connect RST to pin 9
// #define PIN_DC    8                                                    // Connect DC to pin 8
// #define DC_JUMPER 0                                                    // Set to either 0 (SPI, default) or 1 (I2C) based on jumper, matching the value of the DC Jumper
// MicroOLED oled(PIN_RESET, PIN_DC, CS_OLED);                             //SPI declaration
//
byte secs, mins, hours = 0;
bool Display = false;




// Gyroscope
#define MPU_ADDR 0x068                                                 // I2C address of the MPU-6050
byte mpu_sampling = 1;

long gyro_x_cal, gyro_y_cal, gyro_z_cal;
short gyro_x, gyro_y, gyro_z;
short acc_x, acc_y, acc_z;
short temp_mpu;
bool mpu_Enable = false;




//  Time Keeping
volatile unsigned long msecs = 0;
volatile unsigned long oldmsecs = 0;
volatile unsigned long ledMsecs = 0;
volatile unsigned long mpuMsecs = 0;
unsigned long refSec = 0;
unsigned short ref_led_msecs = 0;
unsigned short ref_mpu_msecs = 0;
byte light_Cycle = -1;

volatile int interruptCounter;
int totalInterruptCounter;
hw_timer_t * timer = NULL;
portMUX_TYPE timerMux = portMUX_INITIALIZER_UNLOCKED;




//////////////////////////////////////////////////////////////////////////////////
//
// Functions
//
//////////////////////////////

                                  // TIMING FUNCTIONS

void processTime(){
  secs++;
  if (secs >= 60){
  mins++;
  secs = 0;
  if (mins >= 60){
    mins = 0;
    hours++;
    }
  }
}

// LIGHT DETECTOR FUNCTIONS

void process_light_sensor(){

unsigned short na = cnta - oldcnta;
oldcnta = cnta;
Ia = ((float)na*light_sampling);

}

void write_potentiometer(int value){
Serial.print("SLI ");
Serial.print(value);
Serial.println("$");
digitalWrite(POT_PIN, LOW);
SPI.transfer(POT_ADDR);
SPI.transfer(value);
digitalWrite(POT_PIN, HIGH);
}

void check_Light(){
if ((msecs - ledMsecs >= (1000/light_sampling)) and sensor_Enable){
//      Serial.println((String)"#" + msecs);                          //DEBUG: Used to check process' period
ledMsecs = msecs;
light_Cycle = 1;
process_light_sensor();
//      Serial.println((String)"#" + msecs);                          //DEBUG: Used to check process' period
  }
}


                                  // SERIAL FUNCTIONS

unsigned int getSerialIntArgument(){
  return atoi(serialBuffer+(bufferPos+1) );
}

unsigned long getSerialLongArgument(){
  return atol(serialBuffer+(bufferPos+1) );
}

float getSerialFloatArgument(){
  return atof(serialBuffer+(bufferPos+1) );
}

void processSerialBuffer(){                                          // Subroutine for processing commands in Serial Buffer
  if( toupper(serialBuffer[bufferPos]) == 'L'){
    if( toupper(serialBuffer[bufferPos+1]) == 'O'){
      if( toupper(serialBuffer[bufferPos+2]) == 'N'){
        // LON - Laser ON
        lightOn = true;
        Serial.print("Light On: ");
        Serial.print(lightOn);
        Serial.println("$");
        digitalWrite(LIGHT_PIN, HIGH);
      }
      else if( toupper(serialBuffer[bufferPos+2]) == 'F'){
        // LOF - Laser OF
        lightOn = false;
        Serial.print("Light On: ");
        Serial.print(lightOn);
        Serial.println("$");
        digitalWrite(LIGHT_PIN, LOW);
      }
    }
  }

  if( toupper(serialBuffer[bufferPos]) == 'D'){
    if( toupper(serialBuffer[bufferPos+1]) == 'O'){
      if( toupper(serialBuffer[bufferPos+2]) == 'N'){
        // DON - Display ON
        Display = true;
        Serial.println("Display On$");
      }
      else if( toupper(serialBuffer[bufferPos+2]) == 'F'){
        // DOF - Display OFF
        Display = false;
        Serial.println("Display Off$");
        // oled.clear(PAGE);
        // oled.display();
      }
    }
  }

  if( toupper(serialBuffer[bufferPos]) == 'M'){
    if( toupper(serialBuffer[bufferPos+1]) == 'O'){
      if( toupper(serialBuffer[bufferPos+2]) == 'N'){
        // DON - Display ON
        mpu_Enable = true;
        Serial.println("MPU Enabled$");
      }
      else if( toupper(serialBuffer[bufferPos+2]) == 'F'){
        // DOF - Display OFF
        mpu_Enable = false;
        Serial.println("MPU Disabled$");
      }
    }
  }

  if( toupper(serialBuffer[bufferPos]) == 'S'){
    if( toupper(serialBuffer[bufferPos+1]) == 'L'){
      if( toupper(serialBuffer[bufferPos+2]) == 'I'){
        // SLI - Set Light Intensity
        bufferPos += 3;
        light_int = getSerialLongArgument();
        write_potentiometer(light_int);
      }
      if( toupper(serialBuffer[bufferPos+2]) == 'S'){
        // SMS - Set MPU Sampling
        bufferPos += 3;
        light_sampling = getSerialIntArgument();
        Serial.print("Light Sampling set to: ");
        Serial.print(light_sampling);
        Serial.println("$");
      }
    }
    if( toupper(serialBuffer[bufferPos+1]) == 'M'){
      if( toupper(serialBuffer[bufferPos+2]) == 'S'){
        // SMS - Set MPU Sampling
        bufferPos += 3;
        mpu_sampling = getSerialIntArgument();
        Serial.print("MPU Sampling set to: ");
        Serial.print(mpu_sampling);
        Serial.println("$");
        }
    }
    if( toupper(serialBuffer[bufferPos+1]) == 'O'){
        if( toupper(serialBuffer[bufferPos+2]) == 'N'){
          // DON - Sensor ON
          sensor_Enable = true;
          Serial.println("Sensor Enabled$");
        }
      else if( toupper(serialBuffer[bufferPos+2]) == 'F'){
        // DOF - Sensor OFF
        sensor_Enable = false;
        Serial.println("Sensor Disabled$");
      }
    }
  }
}

void read_SERIAL(){                                                  // Subroutine for reading Serial Buffer
  if (Serial.available() > 0) {
    // get incoming byte:
    serialBuffer[bufferEnd] = Serial.read();
    Serial.print(serialBuffer[bufferEnd]);

    // min message length? -> process commands
    if( serialBuffer[bufferEnd] == 10 ) {
      processSerialBuffer();

      // go to message end
      bufferPos = bufferEnd+1;
    }

    if( bufferEnd < SERIAL_BUFFER_LEN - 1 )
      bufferEnd++;
    else
      bufferEnd = 0;
  }
}


void write_SERIAL_LED(){                                                 //Subroutine for writing toSerial
  Serial.print("\tms=");
  Serial.print(ref_led_msecs);
  Serial.print("\tI=");
  Serial.print((float)Ia);
  Serial.print("\tl=");
  Serial.print(lightOn);
  // Serial.print("\ttm=");
  // Serial.print((int)temp_mpu);
  Serial.println("$");
}


// void write_SERIAL_MPU(){                                                 //Subroutine for writing toSerial
//   Serial.print("\tms=");
// //  Serial.print("\t");
//   Serial.print(ref_mpu_msecs);
//   Serial.print("\tgx=");
// //  Serial.print("\t");
//   Serial.print((short)gyro_x);
//   Serial.print("\tgy=");
// //  Serial.print("\t");
//   Serial.print((short)gyro_y);
//   Serial.print("\tgz=");
// //  Serial.print("\t");
//   Serial.print((short)gyro_z);
//   Serial.print("\tax=");
// //  Serial.print("\t");
//   Serial.print((short)acc_x);
//   Serial.print("\tay=");
// //  Serial.print("\t");
//   Serial.print((short)acc_y);
//   Serial.print("\taz=");
// //  Serial.print("\t");
//   Serial.print((short)acc_z);
//   Serial.println("$");
// }
//
//
// void write_SERIAL_CAL(){                                                    //Subroutine for writing toSerial
//   Serial.print("\tgxc=");
// //  Serial.print("\t");
//   Serial.print((short)gyro_x_cal);
//   Serial.print("\tgyc=");
// //  Serial.print("\t");
//   Serial.print((short)gyro_y_cal);
//   Serial.print("\tgzc=");
// //  Serial.print("\t");
//   Serial.print((short)gyro_z_cal);
//   Serial.println("$");
// }




//            Light Switch

byte display_Switch(byte light_Cycle){

  switch(light_Cycle){

    case 1:
      light_Cycle++;
      write_SERIAL_LED();
      ref_led_msecs += (1000/light_sampling);
      return(light_Cycle);

    case 2:
      processTime();
      if (Display){light_Cycle++;}
      else{light_Cycle = 0;}
      return(light_Cycle);
    //
    // case 3:
    //   // oledProcess1();
    //   light_Cycle++;
    //   return(light_Cycle);
    //
    // case 4:
    //   // oledProcess2();
    //   light_Cycle++;
    //   return(light_Cycle);
    //
    // case 5:
    //   // oledProcess3();
    //   light_Cycle++;
    //   return(light_Cycle);
    //
    // case 6:
    //   // oledProcess4();
    //   light_Cycle++;
    //   return(light_Cycle);
    //
    // case 7:
    //   // oledProcess5();
    //   light_Cycle++;
    //   return(light_Cycle);

    default:
      read_SERIAL();
      return(light_Cycle);
  }
}



//                                   // MPU 6050 FUNCTIONS
//
//
// void setup_mpu_6050_registers(){
//
//   //Activate the MPU-6050
//   Wire.beginTransmission(0x68);                                        //Start communicating with the MPU-6050
//   Wire.write(0x6B);                                                    //Send the requested starting register
//   Wire.write(0x00);                                                    //Set the requested starting register
//   Wire.endTransmission();                                              //End the transmission
//   //Configure the accelerometer (+/-8g)
//   Wire.beginTransmission(0x68);                                        //Start communicating with the MPU-6050
//   Wire.write(0x1C);                                                    //Send the requested starting register
//   Wire.write(0x10);                                                    //Set the requested starting register
//   Wire.endTransmission();                                              //End the transmission
//   //Configure the gyro (500dps full scale)
//   Wire.beginTransmission(0x68);                                        //Start communicating with the MPU-6050
//   Wire.write(0x1B);                                                    //Send the requested starting register
//   Wire.write(0x08);                                                    //Set the requested starting register
//   Wire.endTransmission();                                              //End the transmission
// }
//
//
//
//
// void calibrate_Gyro(){
//   oled.clear(PAGE);                                                    // Clear the buffer.
//   oled.setCursor(0, 0);                                                // Set cursor to top-left
//   oled.setFontType(0);                                                 // Smallest font
//   oled.print("GYRO CAL");
//   oled.setCursor(0, 16);                                               // Set cursor to top-middle-left
//   oled.print("DONT");
//   oled.setCursor(0, 32);
//   oled.print("MOVE");
//   oled.display();
//   Serial.println("CALIBRATING$");
//
//   for (int cal_int = 0; cal_int < 2000 ; cal_int ++){                  //Run this code 2000 times
//     read_mpu_6050_data();                                              //Read the raw acc and gyro data from the MPU-6050
//     gyro_x_cal += gyro_x;                                              //Add the gyro x-axis offset to the gyro_x_cal variable
//     gyro_y_cal += gyro_y;                                              //Add the gyro y-axis offset to the gyro_y_cal variable
//     gyro_z_cal += gyro_z;                                              //Add the gyro z-axis offset to the gyro_z_cal variable
//     delay(3);                                                          //Delay 3us to simulate the 250Hz program loop
//   }
//   gyro_x_cal /= 2000;                                                  //Divide the gyro_x_cal variable by 2000 to get the average offset
//   gyro_y_cal /= 2000;                                                  //Divide the gyro_y_cal variable by 2000 to get the average offset
//   gyro_z_cal /= 2000;                                                  //Divide the gyro_z_cal variable by 2000 to get the average offset
//
//   oled.clear(PAGE);
//   printTitle("Done", 0);
//   Serial.println("CALIBRATION DONE$");
//   write_SERIAL_CAL();
//   delay(1000);
//   oled.clear(PAGE);
//   oled.display();
// }
//
//
// void check_MPU(){
//   if ( (msecs - mpuMsecs >= (1000/mpu_sampling)) and (mpu_Enable)){
// //    Serial.println((String)"$" + msecs);                          //DEBUG: Used to check process' period
//     mpuMsecs = msecs;
//     read_mpu_6050_data();
//     write_SERIAL_MPU();
//     ref_mpu_msecs += (1000/mpu_sampling);
// //    Serial.println((String)"$" + msecs);                          //DEBUG: Used to check process' period
//   }
// }
//
//
// void read_mpu_6050_data(){                                             //Subroutine for reading the raw gyro and accelerometer data
//   Wire.beginTransmission(0x68);                                        //Start communicating with the MPU-6050
//   Wire.write(0x3B);                                                    //Send the requested starting register
//   Wire.endTransmission();                                              //End the transmission
//   Wire.requestFrom(0x68,14);                                           //Request 14 bytes from the MPU-6050
//   while(Wire.available() < 14);                                        //Wait until all the bytes are received
//   acc_x = Wire.read()<<8|Wire.read();                                  //Add the low and high byte to the acc_x variable
//   acc_y = Wire.read()<<8|Wire.read();                                  //Add the low and high byte to the acc_y variable
//   acc_z = Wire.read()<<8|Wire.read();                                  //Add the low and high byte to the acc_z variable
//   temp_mpu = Wire.read()<<8|Wire.read();                               //Add the low and high byte to the temperature variable
//   gyro_x = Wire.read()<<8|Wire.read();                                 //Add the low and high byte to the raw_gyro_x variable
//   gyro_y= Wire.read()<<8|Wire.read();                                  //Add the low and high byte to the raw_gyro_yvariable
//   gyro_z= Wire.read()<<8|Wire.read();                                  //Add the low and high byte to the raw_gyro_zvariable
//
// }
//
//
//                                   // INTERRUPT ROUTINES
//                                                                        // Timer code was adapated from https://techtutorialsx.com/2017/10/07/esp32-arduino-timer-interrupts/
//

void IRAM_ATTR onTimer() {                                                // Subroutine that describes what happens when the internal timer overflow. IRAM_ATTR is added "in order for the compiler to place the code in IRAM. Also, interrupt handling routines should only call functions also placed in IRAM"
  portENTER_CRITICAL_ISR(&timerMux);                                      // Locks process to avoid concurrency issues but doesnt allow other core to load a seperate thread, which would be inefficient since code is so short.
  interruptCounter++;
  portEXIT_CRITICAL_ISR(&timerMux);

}

void isr1(){
  cnta++;
}



                                   // DISPLAY FUNCTIONS
// void oledSetup(){
//   oled.begin();                                                        // Initialize the OLED
//   oled.clear(ALL);                                                     // Clear the display's internal memory
//   oled.display();
//   delay(1000);
//   oled.clear(PAGE);                                                   // Clear the buffer.
//   oled.setCursor(0, 0);                                               // Set cursor to top-left
//   oled.setFontType(0);                                                // Smallest font
//   oled.print("SMART");
//   oled.setCursor(0, 16);                                              // Set cursor to top-middle-left
//   oled.print("CLAMP");
//   oled.setCursor(0, 32);
//   oled.print((String)"V."+ SMARTCLAMP_VERSION);
//   oled.display();
//   delay(2000);                                                        // Delay so user may see start screen
//   oled.clear(PAGE);                                                   // Clear the buffer.
// }
//
// void registers_Error(){
//   oled.clear(PAGE);                                                   // Clear the buffer.
//   oled.setCursor(0, 0);                                               // Set cursor to top-left
//   oled.setFontType(0);                                                // Smallest font
//   oled.print("MPU REG");
//   oled.setCursor(0, 16);                                              // Set cursor to top-middle-left
//   oled.print("ERROR");
//   oled.setCursor(0, 32);
//   oled.print("RESET");
//   oled.display();
// }
//
// void printTitle(String title, int font){
//   oled.clear(PAGE);
//   int middleX = oled.getLCDWidth() / 2;
//   int middleY = oled.getLCDHeight() / 2;
//
//   oled.clear(PAGE);
//   oled.setFontType(font);
//   // Try to set the cursor in the middle of the screen
//   oled.setCursor(middleX - (oled.getFontWidth() * (title.length() / 2)),
//                  middleY - (oled.getFontHeight() / 2));
//   // Print the title:
//   oled.print(title);
//   oled.display();
// }
//
// void oledProcess1(){
//   oled.clear(PAGE);                                                   // Clear the display
//   oled.setCursor(0, 0);                                               // Set cursor to top-left
//   oled.setFontType(0);                                                // Smallest font
//   oled.print("T:");                                                   // Print "T"
// }
//
// void oledProcess2(){
//   if (hours > 0){
//     oled.print((String)hours + ":");
//   }
//   if (secs >= 10){
//     oled.print((String)mins+":"+secs);
//   }else{
//     oled.print((String)mins+":0"+secs);
//   }
// }
//
// void oledProcess3(){
//   oled.setCursor(0, 16);                                               // Set cursor to top-middle-left
//   oled.print("I:");
//   oled.print(Ia);
//   }
//
// void oledProcess4(){
//   oled.setCursor(0, 32);
//   oled.print("LED: ");
//   oled.setFontType(1);
//   if (lightOn){
//     oled.print("ON");
//   }else{
//     oled.print("OFF");
//   }
// }
//
// void oledProcess5(){
//   oled.display();
//   }
//
//
//
//
//


///////////////////////////////////////////////////////////////////
//
// SETUP
//


void setup() {
  //Initialization
  // Wire.begin();                                                        //Start I2C as master
  Serial.begin(115200);                                                 //Start Serial Channel
  timer = timerBegin(0, 80, true);
  timerAttachInterrupt(timer, &onTimer, true);
  timerAlarmWrite(timer, 1000, true);
  timerAlarmEnable(timer);

  Serial.println("START$");                                            //Let PC know program started
  Serial.println((String)"SMARTCLAMP version: " + SMARTCLAMP_VERSION + "$");
  // oledSetup();


  // Pin Declarations
  pinMode(SENSOR_A_PIN, INPUT);                                        //Set Light Sensor as Input
  digitalWrite(SENSOR_A_PIN, HIGH);

  pinMode(LIGHT_PIN, OUTPUT);                                          //Set Light Pin as Output
  digitalWrite(LIGHT_PIN, LOW);                                        //Start Light Source as Off

  pinMode(POT_PIN, OUTPUT);                                            // Set Potentiometer's CS pin for SPI as Output


  // MPU Setup
  // registers_Error();
  // setup_mpu_6050_registers();                                          //Setup the registers of the MPU-6050 (500dfs / +/-8g) and start the gyro
  // calibrate_Gyro();

  SPI.begin();
  write_potentiometer((byte)128);
  attachInterrupt(digitalPinToInterrupt(27), isr1, RISING);                                    //Interrupt function isr1 triggered by rising edge at PIN D2
  Serial.println("READY$");
}


///////////////////////////////////////////////////////////////////
//
// Main Loop
//


void loop() {

  if (interruptCounter > 0) {

    portENTER_CRITICAL(&timerMux);
    interruptCounter--;
    portEXIT_CRITICAL(&timerMux);

    // totalInterruptCounter++;
    msecs++;

    if(msecs - oldmsecs >= 1000){
      oldmsecs = msecs;
      refSec++;
      ref_led_msecs = 0;
      ref_mpu_msecs = 0;
      Serial.print("\tt=");
      Serial.print((int)refSec);
      Serial.println("$");
    }

    light_Cycle = display_Switch(light_Cycle);
    // check_MPU();
    check_Light();

  }
}
