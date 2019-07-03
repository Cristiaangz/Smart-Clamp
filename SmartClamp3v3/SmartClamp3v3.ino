/*
 *    FILE: SmartClamp.ino
 *  AUTHOR: Cristian Garcia (Based on turbidostat.ino by Christian Wohltat, Stefan Hoffman)
 *    DATE: 2019 19 01
 */

//////////////////////////////////////////////////////////////////////////////////
//
//  Definitions and Declarations
//
//////////////////////////////


#define SMARTCLAMP_VERSION  "0.12"
#include <PinChangeInt.h>                                              // DEPRECATED: Should consider chanaging to EnableInterrupt.h Library when given the time
#include <Wire.h>                                                      //Enables I2C Comms
#include <SPI.h>                                                       //Enables SPI Comms
#include <SFE_MicroOLED.h>                                             // Include the SFE_MicroOLED library
//#include <MPU6050_tockn>                                             //MPU6050 reference library




//Serial Comms
#define SERIAL_BUFFER_LEN 128                                          // Defines Arduino buffer as 128 bytes instead of 64                                                  // Interval of sent data
char serialBuffer[SERIAL_BUFFER_LEN];
unsigned short bufferEnd = 0;
unsigned short bufferPos = 0;




// Light Detection
#define SENSOR_A_PIN  2
#define LIGHT_PIN     4
#define POT_PIN       5
#define POT_ADDR      0x00

bool lightOn = false;
volatile unsigned long cnta = 0;
unsigned long oldcnta = 0;
float Ia = 0;                                                          // current intensity of sensor A in uW/m2
byte light_int = 128;                                                  //Changes potentiometer resistance from 10kΩ to 0Ω [0-128]




// OLED Display
#define CS_OLED   10
#define PIN_RESET 9                                                    // Connect RST to pin 9
#define PIN_DC    8                                                    // Connect DC to pin 8
#define DC_JUMPER 0                                                    // Set to either 0 (SPI, default) or 1 (I2C) based on jumper, matching the value of the DC Jumper
MicroOLED oled(PIN_RESET, PIN_DC, CS_OLED);                             //SPI declaration

byte secs, mins, hours = 0;
bool Display = false;




// Gyroscope
#define MPU_ADDR 0x068                                                 // I2C address of the MPU-6050
byte MPU_SAMPLING = 5;

long gyro_x_cal, gyro_y_cal, gyro_z_cal;
short gyro_x, gyro_y, gyro_z;
short acc_x, acc_y, acc_z;
short temp_mpu;




//  Time Keeping
volatile unsigned long msecs = 0;
volatile unsigned long oldmsecs = 0;
volatile unsigned long mpumsecs = 0;
unsigned long refTime = 0;
unsigned short refMsecs = 0;
byte sec_Cycle = -1;
bool mpu_Cycle = false;




///////////////////////////////////////////////////////////////////
//
// SETUP
//


void setup() {
  //Initialization
  Wire.begin();                                                        //Start I2C as master
  Serial.begin(57600);                                                 //Start Serial Channel
  Serial.println("START$");                                            //Let PC know program started  
  Serial.println((String)"SMARTCLAMP version: " + SMARTCLAMP_VERSION + "$");
  oledSetup();

  // Pin Declarations
  pinMode(SENSOR_A_PIN, INPUT);                                        //Set Light Sensor as Input
  digitalWrite(SENSOR_A_PIN, HIGH);

  pinMode(LIGHT_PIN, OUTPUT);                                          //Set Light Pin as Output
  digitalWrite(LIGHT_PIN, LOW);                                        //Start Light Source as Off

  pinMode(POT_PIN, OUTPUT);                                            // Set Potentiometer's CS pin for SPI as Output


  // MPU Setup
  registers_Error();
  setup_mpu_6050_registers();                                          //Setup the registers of the MPU-6050 (500dfs / +/-8g) and start the gyro
  calibrate_Gyro();

  SPI.begin();
  write_potentiometer((byte)128);
  attachInterrupt(0, isr1, RISING);                                    //Interrupt function isr1 triggered by rising edge at PIN D2
  Timer2init();
}


///////////////////////////////////////////////////////////////////
//
// Main Loop
//


void loop() {

  switch(sec_Cycle){

    
    case 1:
//      Serial.println((String)"$" + msecs);                          //DEBUG: Used to check process' period
      process_light_sensor();
      sec_Cycle++;
//      Serial.println((String)"#" + msecs);
      break;

    case 2:
      write_SERIAL_1HZ();
      sec_Cycle++;
      break;

    case 3:
      processTime();
      if (Display){sec_Cycle++;}
      else{sec_Cycle = 0;}
      break;

    case 4:
      oledProcess1();
      sec_Cycle++;
      break;

    case 5:
      oledProcess2();
      sec_Cycle++;
      break;

    case 6:
      oledProcess3();
      sec_Cycle++;
      break;

    case 7:
      oledProcess4();
      sec_Cycle++;
      break;

    case 8:
      oledProcess5();
      sec_Cycle++;
      break;

    default:
      read_SERIAL();
  }
  
  check_MPU();
  
  if (msecs - oldmsecs >= 1000){
    oldmsecs = msecs;
    refMsecs = 0;
    refTime++;
    sec_Cycle = 1;
  }
}

void check_MPU(){
  if ( (msecs - mpumsecs >= (1000/MPU_SAMPLING)) and (refMsecs < 1000)){
    mpumsecs = msecs;
    read_mpu_6050_data();
    write_SERIAL_MPU();
    refMsecs += (1000/MPU_SAMPLING);
  }
}

//////////////////////////////////////////////////////////////////////////////////
//
// Functions
//
//////////////////////////////


                                  // SERIAL FUNCTIONS
                                  

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

void processSerialBuffer(){                                          // Subroutine for processing commands in Serial Buffer
  if( toupper(serialBuffer[bufferPos]) == 'L'){
    if( toupper(serialBuffer[bufferPos+1]) == 'O'){
      if( toupper(serialBuffer[bufferPos+2]) == 'N'){
        // LON - Laser ON
        lightOn = true;
        Serial.print("Light On: ");
        Serial.println(lightOn);
        digitalWrite(LIGHT_PIN, HIGH);
      }
      else if( toupper(serialBuffer[bufferPos+2]) == 'F'){
        // LOF - Laser OF
        lightOn = false;
        Serial.print("Light On: ");
        Serial.println(lightOn);
        digitalWrite(LIGHT_PIN, LOW);
      }
    }
  }

  if( toupper(serialBuffer[bufferPos]) == 'D'){
    if( toupper(serialBuffer[bufferPos+1]) == 'O'){
      if( toupper(serialBuffer[bufferPos+2]) == 'N'){
        // DON - Display ON
        Display = true;
//        Serial.println("Display On");
      }
      else if( toupper(serialBuffer[bufferPos+2]) == 'F'){
        // DOF - Display OFF
        Display = false;
//        Serial.println("Display Off");
        oled.clear(PAGE);
        oled.display();  
      }
    }
  }
  
  if( toupper(serialBuffer[bufferPos]) == 'S'){
    if( toupper(serialBuffer[bufferPos+1]) == 'L'){
      if( toupper(serialBuffer[bufferPos+2]) == 'I'){
        // SLI - Set Light Intensity
        bufferPos += 3;
        light_int = getSerialIntArgument();
        write_potentiometer(light_int);
        }
      }
    if( toupper(serialBuffer[bufferPos+1]) == 'M'){
      if( toupper(serialBuffer[bufferPos+2]) == 'S'){
        // SMS - Set MPU Sampling
        bufferPos += 3;
        MPU_SAMPLING = getSerialIntArgument();
        }
      }
    }
  }

void write_SERIAL_1HZ(){                                                 //Subroutine for writing toSerial
  Serial.print("\tt=");
  Serial.print((float)refTime);
  Serial.print("\tI=");
  Serial.print((float)Ia);
  Serial.print("\tl=");
  Serial.print(lightOn);
  Serial.print("\ttm=");
  Serial.print((int)temp_mpu);
//  Serial.print("\tta=");
//  Serial.print(getArduinoTemp(),2);
  Serial.println("$");
}


void write_SERIAL_MPU(){                                                 //Subroutine for writing toSerial
  Serial.print("\tr=");
//  Serial.print("\t");
  Serial.print(refMsecs);
  Serial.print("\tgx=");
//  Serial.print("\t");
  Serial.print((short)gyro_x);
  Serial.print("\tgy=");
//  Serial.print("\t");
  Serial.print((short)gyro_y);
  Serial.print("\tgz=");
//  Serial.print("\t");
  Serial.print((short)gyro_z);
  Serial.print("\tax=");
//  Serial.print("\t");
  Serial.print((short)acc_x);
  Serial.print("\tay=");
//  Serial.print("\t");
  Serial.print((short)acc_y);
  Serial.print("\taz=");
//  Serial.print("\t");
  Serial.print((short)acc_z);
  Serial.println("$");
}


void write_SERIAL_CAL(){                                                    //Subroutine for writing toSerial
  Serial.print("\tgxc=");
//  Serial.print("\t");
  Serial.print((short)gyro_x_cal);
  Serial.print("\tgyc=");
//  Serial.print("\t");
  Serial.print((short)gyro_y_cal);
  Serial.print("\tgzc=");
//  Serial.print("\t");
  Serial.print((short)gyro_z_cal);
  Serial.println("$");
}

unsigned long getSerialIntArgument(){
  return atol(serialBuffer+(bufferPos+1) );
}

float getSerialFloatArgument(){
  return atof(serialBuffer+(bufferPos+1) );
}






                                  // LIGHT DETECTOR FUNCTIONS

void process_light_sensor(){
  
  unsigned short na = cnta - oldcnta;
  oldcnta = cnta;
  Ia = ((float)na/6);
  
}

void write_potentiometer(int value)
{
digitalWrite(POT_PIN, LOW);
SPI.transfer(POT_ADDR);
SPI.transfer(value);
digitalWrite(POT_PIN, HIGH);
}






                                  // MPU 6050 FUNCTIONS


void setup_mpu_6050_registers(){
  
  //Activate the MPU-6050
  Wire.beginTransmission(0x68);                                        //Start communicating with the MPU-6050
  Wire.write(0x6B);                                                    //Send the requested starting register
  Wire.write(0x00);                                                    //Set the requested starting register
  Wire.endTransmission();                                              //End the transmission
  //Configure the accelerometer (+/-8g)
  Wire.beginTransmission(0x68);                                        //Start communicating with the MPU-6050
  Wire.write(0x1C);                                                    //Send the requested starting register
  Wire.write(0x10);                                                    //Set the requested starting register
  Wire.endTransmission();                                              //End the transmission
  //Configure the gyro (500dps full scale)
  Wire.beginTransmission(0x68);                                        //Start communicating with the MPU-6050
  Wire.write(0x1B);                                                    //Send the requested starting register
  Wire.write(0x08);                                                    //Set the requested starting register
  Wire.endTransmission();                                              //End the transmission
}

void calibrate_Gyro(){
  oled.clear(PAGE);                                                    // Clear the buffer.
  oled.setCursor(0, 0);                                                // Set cursor to top-left
  oled.setFontType(0);                                                 // Smallest font
  oled.print("GYRO CAL");
  oled.setCursor(0, 16);                                               // Set cursor to top-middle-left
  oled.print("DONT");
  oled.setCursor(0, 32);
  oled.print("MOVE");
  oled.display();
  Serial.println("CALIBRATING$"); 
  
  for (int cal_int = 0; cal_int < 2000 ; cal_int ++){                  //Run this code 2000 times
    read_mpu_6050_data();                                              //Read the raw acc and gyro data from the MPU-6050
    gyro_x_cal += gyro_x;                                              //Add the gyro x-axis offset to the gyro_x_cal variable
    gyro_y_cal += gyro_y;                                              //Add the gyro y-axis offset to the gyro_y_cal variable
    gyro_z_cal += gyro_z;                                              //Add the gyro z-axis offset to the gyro_z_cal variable
    delay(3);                                                          //Delay 3us to simulate the 250Hz program loop
  }
  gyro_x_cal /= 2000;                                                  //Divide the gyro_x_cal variable by 2000 to get the average offset
  gyro_y_cal /= 2000;                                                  //Divide the gyro_y_cal variable by 2000 to get the average offset
  gyro_z_cal /= 2000;                                                  //Divide the gyro_z_cal variable by 2000 to get the average offset

  oled.clear(PAGE);
  printTitle("Done", 0);
  Serial.println("CALIBRATION DONE$");
  write_SERIAL_CAL();
  delay(1000);
  oled.clear(PAGE);
  oled.display(); 
}

void read_mpu_6050_data(){                                             //Subroutine for reading the raw gyro and accelerometer data
  Wire.beginTransmission(0x68);                                        //Start communicating with the MPU-6050
  Wire.write(0x3B);                                                    //Send the requested starting register
  Wire.endTransmission();                                              //End the transmission
  Wire.requestFrom(0x68,14);                                           //Request 14 bytes from the MPU-6050
  while(Wire.available() < 14);                                        //Wait until all the bytes are received
  acc_x = Wire.read()<<8|Wire.read();                                  //Add the low and high byte to the acc_x variable
  acc_y = Wire.read()<<8|Wire.read();                                  //Add the low and high byte to the acc_y variable
  acc_z = Wire.read()<<8|Wire.read();                                  //Add the low and high byte to the acc_z variable
  temp_mpu = Wire.read()<<8|Wire.read();                               //Add the low and high byte to the temperature variable
  gyro_x = Wire.read()<<8|Wire.read();                                 //Add the low and high byte to the raw_gyro_x variable
  gyro_y= Wire.read()<<8|Wire.read();                                  //Add the low and high byte to the raw_gyro_yvariable
  gyro_z= Wire.read()<<8|Wire.read();                                  //Add the low and high byte to the raw_gyro_zvariable

}

void process_mpu_6050_data(){
  //Gyro Angle Calibration Offset
  gyro_x -= (short)gyro_x_cal;                                            //Subtract the offset calibration value from the raw_gyro_x value
  gyro_y -= (short)gyro_y_cal;                                            //Subtract the offset calibration value from the raw_gyro_yvalue
  gyro_z -= (short)gyro_z_cal;                                            //Subtract the offset calibration value from the raw_gyro_zvalue
  
  //Gyro angle calculations (Raw Gyro) = ( 1 º/S) * (65.5 s/º)
  //Accelerometer angle calculations (Raw Acc) = (1 g) * (4,096 / g)
  
}







                                  // INTERRUPT ROUTINES


void isr1()
{
  cnta++;
}


void Timer2init() {

    // Setup Timer2 overflow to fire every 8ms (125Hz)
    //   period [sec] = (1 / f_clock [sec]) * prescale * (255-count)
    //                  (1/8000000)  * 64 * (255-130) = .008 sec

    TCCR2B = 0x00;                                                      // Disable Timer2 while we set it up

    TCNT2  = 130;                                                       // Reset Timer Count  (255-130) = execute ev 125-th T/C clock
    TIFR2  = 0x00;                                                      // Timer2 INT Flag Reg: Clear Timer Overflow Flag
    TIMSK2 = 0x01;                                                      // Timer2 INT Reg: Timer2 Overflow Interrupt Enable
    TCCR2A = 0x00;                                                      // Timer2 Control Reg A: Wave Gen Mode normal
    TCCR2B = 0x04;                                                      // Timer2 Control Reg B: Timer Prescaler set to 1024
}

ISR(TIMER2_OVF_vect) {
  //static unsigned char count;                                           // interrupt counter

  //if( (++count & 0x01) == 0 )                                         // bump the interrupt counter
    ++msecs;                                                            // & count uSec every other time.
  TCNT2 = 256-125;                                                      // reset counter every 125th time (125*4us = 1ms)
  TIFR2 = 0x00;                                                         // clear timer overflow flag
};








                                  // DISPLAY FUNCTIONS
void oledSetup(){
  oled.begin();                                                        // Initialize the OLED
  oled.clear(ALL);                                                     // Clear the display's internal memory
  oled.display();
  delay(1000);
  oled.clear(PAGE);                                                   // Clear the buffer.
  oled.setCursor(0, 0);                                               // Set cursor to top-left
  oled.setFontType(0);                                                // Smallest font
  oled.print("SMART");
  oled.setCursor(0, 16);                                              // Set cursor to top-middle-left
  oled.print("CLAMP");
  oled.setCursor(0, 32);
  oled.print((String)"V."+ SMARTCLAMP_VERSION);
  oled.display();
  delay(2000);                                                        // Delay so user may see start screen
  oled.clear(PAGE);                                                   // Clear the buffer.
}

void registers_Error(){
  oled.clear(PAGE);                                                   // Clear the buffer.
  oled.setCursor(0, 0);                                               // Set cursor to top-left
  oled.setFontType(0);                                                // Smallest font
  oled.print("MPU REG");
  oled.setCursor(0, 16);                                              // Set cursor to top-middle-left
  oled.print("ERROR");
  oled.setCursor(0, 32);
  oled.print("RESET");
  oled.display();
}

void printTitle(String title, int font)
{
  oled.clear(PAGE);
  int middleX = oled.getLCDWidth() / 2;
  int middleY = oled.getLCDHeight() / 2;

  oled.clear(PAGE);
  oled.setFontType(font);
  // Try to set the cursor in the middle of the screen
  oled.setCursor(middleX - (oled.getFontWidth() * (title.length() / 2)),
                 middleY - (oled.getFontHeight() / 2));
  // Print the title:
  oled.print(title);
  oled.display();
}

void oledProcess1(){
  oled.clear(PAGE);                                                   // Clear the display
  oled.setCursor(0, 0);                                               // Set cursor to top-left
  oled.setFontType(0);                                                // Smallest font
  oled.print("T:");                                                   // Print "T"
}

void oledProcess2(){
  if (hours > 0){
    oled.print((String)hours + ":");  
  }
  if (secs >= 10){
    oled.print((String)mins+":"+secs);                                
  }else{
    oled.print((String)mins+":0"+secs); 
  }
}

void oledProcess3(){
  oled.setCursor(0, 16);                                               // Set cursor to top-middle-left
  oled.print("I:");
  oled.print(Ia);
  }

void oledProcess4(){
  oled.setCursor(0, 32);
  oled.print("LED: "); 
  oled.setFontType(1);
  if (lightOn){
    oled.print("ON");
  }else{
    oled.print("OFF");
  }
}

void oledProcess5(){
  oled.display();
  }




  
                                  // OTHER FUNCTIONS

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
