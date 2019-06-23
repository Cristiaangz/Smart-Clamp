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


#define SMARTCLAMP_VERSION  "0.11"
#include <PinChangeInt.h>                                              // DEPRECATED: Should consider chanaging to EnableInterrupt.h Library when given the time
#include <Wire.h>                                                      //Enables I2C Comms
#include <SPI.h>                                                       //Enables SPI Comms
//#include <MPU6050_tockn>                                             //MPU6050 Data processing


//Serial Comms
#define SERIAL_BUFFER_LEN 128                                          // Defines Arduino buffer as 128 bytes instead of 64
char serialBuffer[SERIAL_BUFFER_LEN];
unsigned short bufferEnd = 0;
unsigned short bufferPos = 0;

// Light Detection
#define SENSOR_A_PIN  2
#define LIGHT_PIN     4
#define POT_PIN       10
#define POT_ADDR      0x00

volatile unsigned long cnta = 0;
unsigned long oldcnta = 0;
//float OD = 0;
float Ia = 0;                                                          // current intensity of sensor A in uW/m2
unsigned long I = 0;                                                   // current intensity in uW/m2
unsigned long I_0 = 0;                                                 // zero intensity in uW/m2

byte light_int = 128;                                                  //Changes potentiometer resistance from 10kΩ to 0Ω [0-128]


// Gyroscope
#define MPU_ADDR 0x068                                                 // I2C address of the MPU-6050
long gyro_x_cal, gyro_y_cal, gyro_z_cal;
int raw_gyro_x, raw_gyro_y, raw_gyro_z;
float gyro_x, gyro_y, gyro_z;
float acc_x, acc_y, acc_z, acc_mag;
float temp_mpu;


// Modes
bool lightOn = false;

//  Time Keeping
extern volatile unsigned long msecs = 0;
extern volatile unsigned long oldmsecs = 0;
extern volatile unsigned long refTime = 0;



///////////////////////////////////////////////////////////////////
//
// SETUP
//


void setup() {
  //Initialization
  Wire.begin();                                                        //Start I2C as master
  Serial.begin(115200);                                                //Start Serial Channel
  Serial.println("START$");                                             //Let PC know program started
  Serial.print("SMARTCLAMP version: ");
  Serial.print(SMARTCLAMP_VERSION);
  Serial.println("$");
  
  setup_mpu_6050_registers();                                          //Setup the registers of the MPU-6050 (500dfs / +/-8g) and start the gyro

  // Pin Declarations
  pinMode(SENSOR_A_PIN, INPUT);                                        //Set Light Sensor as Input
  digitalWrite(SENSOR_A_PIN, HIGH);

  pinMode(LIGHT_PIN, OUTPUT);                                          //Set Light Pin as Output
  digitalWrite(LIGHT_PIN, LOW);                                        //Start Light Source as Off

  pinMode(13, OUTPUT);                                                 //Set On Board LED as Output

  pinMode(POT_PIN, OUTPUT);

  // Calibration

  digitalWrite(13, HIGH);                                              //Set digital output 13 high to indicate startup
  
  Serial.println("Calibrating gyro$"); 
  
  for (int cal_int = 0; cal_int < 2000 ; cal_int ++){                  //Run this code 2000 times
    read_mpu_6050_data();                                              //Read the raw acc and gyro data from the MPU-6050
    gyro_x_cal += raw_gyro_x;                                              //Add the gyro x-axis offset to the gyro_x_cal variable
    gyro_y_cal += raw_gyro_y;                                              //Add the gyro y-axis offset to the gyro_y_cal variable
    gyro_z_cal += raw_gyro_z;                                              //Add the gyro z-axis offset to the gyro_z_cal variable
    delay(3);                                                          //Delay 3us to simulate the 250Hz program loop
  }
  gyro_x_cal /= 2000;                                                  //Divide the gyro_x_cal variable by 2000 to get the average offset
  gyro_y_cal /= 2000;                                                  //Divide the gyro_y_cal variable by 2000 to get the average offset
  gyro_z_cal /= 2000;                                                  //Divide the gyro_z_cal variable by 2000 to get the average offset

  digitalWrite(13, LOW);

  SPI.begin();
  attachInterrupt(0, isr1, RISING);                                    //Interrupt function isr1 triggered by rising edge at PIN D2
  Timer2init();

  Serial.println("CALIBRATION DONE$");
}


///////////////////////////////////////////////////////////////////
//
// Main Loop
//


void loop() {

  read_SERIAL();
  
  if (msecs - oldmsecs >= 1000){
    
    oldmsecs = msecs;
    refTime++;

    write_potentiometer(light_int);
    
    process_light_sensor();
    read_mpu_6050_data();
    process_mpu_6050_data();
    
    write_SERIAL();

    if (lightOn)  {digitalWrite(LIGHT_PIN, HIGH);}
    else  {digitalWrite(LIGHT_PIN, LOW);}

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
      }
      else if( toupper(serialBuffer[bufferPos+2]) == 'F'){
        // LOF - Laser OF
        lightOn = false;
        Serial.print("Light On: ");
        Serial.println(lightOn);
      }
    }
  }
  if( toupper(serialBuffer[bufferPos]) == 'S'){
    if( toupper(serialBuffer[bufferPos+1]) == 'L'){
      if( toupper(serialBuffer[bufferPos+2]) == 'I'){
        // SLI - Set Light Intensity
        bufferPos += 3;
        light_int = getSerialIntArgument();
        
        }
      }
    }
  }

void write_SERIAL(){                                                 //Subroutine for writing toSerial
  Serial.print("\ttime=");
  Serial.print((unsigned long)refTime);
  Serial.print("\tIa=");
  Serial.print((float)Ia);
  Serial.print("\tlightOn=");
  Serial.print(lightOn);
  Serial.print("\tgyro_x=");
  Serial.print((float)gyro_x);
  Serial.print("\tgyro_y=");
  Serial.print((float)gyro_y);
  Serial.print("\tgyro_z=");
  Serial.print((float)gyro_z);
  Serial.print("\tacc_x=");
  Serial.print((float)acc_x);
  Serial.print("\tacc_y=");
  Serial.print((float)acc_y);
  Serial.print("\tacc_z=");
  Serial.print((float)acc_z);
  Serial.print("\tacc_mag=");
  Serial.print((float)acc_mag);
  Serial.print("\ttemp_mpu=");
  Serial.print((float)temp_mpu);
  Serial.print("\ttemp_ard=");
  Serial.print(getArduinoTemp(),2);
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
  
  unsigned long na = cnta - oldcnta;
  oldcnta = cnta;
  Ia = (na/6);                                                         // Intensity given in Watts per sq meter
  
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
  raw_gyro_x = Wire.read()<<8|Wire.read();                             //Add the low and high byte to the raw_gyro_x variable
  raw_gyro_y= Wire.read()<<8|Wire.read();                              //Add the low and high byte to the raw_gyro_yvariable
  raw_gyro_z= Wire.read()<<8|Wire.read();                              //Add the low and high byte to the raw_gyro_zvariable

}

void process_mpu_6050_data(){
  //Gyro Angle Calibration Offset
  raw_gyro_x -= gyro_x_cal;                                            //Subtract the offset calibration value from the raw_gyro_x value
  raw_gyro_y -= gyro_y_cal;                                            //Subtract the offset calibration value from the raw_gyro_yvalue
  raw_gyro_z -= gyro_z_cal;                                            //Subtract the offset calibration value from the raw_gyro_zvalue
  
  //Gyro angle calculations (Raw Gyro) = ( 1 º/S) * (65.5 s/º)
  gyro_x = raw_gyro_x / 65.5;                                          //Calculate the gyro_x in º/s
  gyro_y = raw_gyro_y / 65.5;                                          //Calculate the gyro_y in º/s
  gyro_z = raw_gyro_z / 65.5;                                          //Calculate the gyro_z in º/s

  
  //Accelerometer angle calculations (Raw Acc) = (1 g) * (4,096 / g)
  acc_mag = (sqrt((acc_x*acc_x)+(acc_y*acc_y)+(acc_z*acc_z)))/4096;   //Calculate the total accelerometer vector
  acc_x /= 4096;                                                      //Calculate the gyro_x in º/s
  acc_y /= 4096;                                                      //Calculate the gyro_y in º/s
  acc_z /= 4096;                                                      //Calculate the gyro_z in º/s

  temp_mpu = (temp_mpu + 11379)/340;
  
}

                                  // INTERRUPT ROUTINES


void isr1()
{
  cnta++;
}

void Timer2init() {

    // Setup Timer2 overflow to fire every 8ms (125Hz)
    //   period [sec] = (1 / f_clock [sec]) * prescale * (255-count)
    //                  (1/16000000)  * 1024 * (255-130) = .008 sec

    TCCR2B = 0x00;                                                      // Disable Timer2 while we set it up

    TCNT2  = 130;                                                       // Reset Timer Count  (255-130) = execute ev 125-th T/C clock
    TIFR2  = 0x00;                                                      // Timer2 INT Flag Reg: Clear Timer Overflow Flag
    TIMSK2 = 0x01;                                                      // Timer2 INT Reg: Timer2 Overflow Interrupt Enable
    TCCR2A = 0x00;                                                      // Timer2 Control Reg A: Wave Gen Mode normal
    TCCR2B = 0x05;                                                      // Timer2 Control Reg B: Timer Prescaler set to 1024
}

ISR(TIMER2_OVF_vect) {
  //static unsigned char count;                                           // interrupt counter

  //if( (++count & 0x01) == 0 )                                         // bump the interrupt counter
    ++msecs;                                                            // & count uSec every other time.
  TCNT2 = 256-125;                                                      // reset counter every 125th time (125*4us = 1ms)
  TIFR2 = 0x00;                                                         // clear timer overflow flag
};



                                  // OTHER FUNCTIONS



double getArduinoTemp(){
  // The internal temperature has to be used
  // with the internal reference of 1.1V.
  // Channel 8 can not be selected with
  // the analogRead function yet.

  // Set the internal reference and mux.
  ADMUX = (_BV(REFS1) | _BV(REFS0) | _BV(MUX3));
  ADCSRA |= _BV(ADEN);  // enable the ADC

  ADCSRA |= _BV(ADSC);  // Start the ADC

  // Detect end-of-conversion
  while (bit_is_set(ADCSRA,ADSC));

  #define TEMP_OFFSET (7)
  #define AD2VOLTS          (1.1/1023.0) //1.1v=1023
  #define VOLTS2DEGCELSIUS  (25.0/0.314)

  // The returned temperature is in degrees Celcius.
  return ADCW * AD2VOLTS * VOLTS2DEGCELSIUS - TEMP_OFFSET;
}
