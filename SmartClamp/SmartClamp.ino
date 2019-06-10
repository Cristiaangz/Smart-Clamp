/*
 *    FILE: SmartClamp.ino
 *  AUTHOR: Cristian Garcia (Based on turbidostat.ino by Christian Wohltat, Stefan Hoffman)
 *    DATE: 2019 06 01
 */

//////////////////////////////////////////////////////////////////////////////////
//
//  Definitions and Declarations
//
//////////////////////////////


#define SMARTCLAMP_VERSION  "0.02"

#define PINMODE
#define FLASH
#include <PinChangeInt.h> // DEPRECATED: Should consider chanaging to EnableInterrupt.h Library when given the time  
#include <EEPROM.h>
#include <avr/eeprom.h>

#define SENSOR_A_PIN  2
#define LASER_PIN   4

volatile unsigned long cnta = 0;
unsigned long oldcnta = 0;
unsigned long t = 0;

#define SERIAL_BUFFER_LEN 128 // Defines Arduino buffer as 128 bytes instead of 64
char serialBuffer[SERIAL_BUFFER_LEN];
unsigned short bufferEnd = 0;
unsigned short bufferPos = 0;

// OD Measurement Parameter
float OD = 0;
unsigned long Ia = 0;         // current intensity of sensor A in uW/m2
unsigned long I = 0;         // current intensity in uW/m2
unsigned long targetI = 0;   // target intensity in uW/m2
unsigned long I_0 = 0;       // zero intensity in uW/m2

// Modes
bool laserOn = false;
bool readSensor = false;



//////////////////////////////////////////////////////////////////////////////////
//
// Third Party Functions
//
//////////////////////////////

void            processSerialBuffer();
unsigned long   getSerialIntArgument();
void            setPwmFrequency(int pin, int divisor);
double          getArduinoTemp(void);
void            setupADC();


// INTERRUPT ROUTINES
void isr1()
{
  cnta++;
}

/*
 * From sample interrupt code published by Noah Stahl on his blog, at:
 * http://arduinomega.blogspot.com/p/arduino-code.html
 *
 */


/*** FUNC

Name:           Timer2init

Function:       Init timer 2 to interrupt periodically. Call this from
                the Arduino setup() function.

Description:    The pre-scaler and the timer count divide the timer-counter
                clock frequency to give a timer overflow interrupt rate:

                Interrupt rate =  16MHz / (prescaler * (255 - TCNT2))

        TCCR2B[b2:0]   Prescaler    Freq [KHz], Period [usec] after prescale
          0x0            (TC stopped)     0         0
          0x1                1        16000.        0.0625
          0x2                8         2000.        0.500
          0x3               32          500.        2.000
          0x4               64          250.        4.000
          0x5              128          125.        8.000
          0x6              256           62.5      16.000
          0x7             1024           15.625    64.000


Parameters: void

Returns:    void

FUNC ***/

void Timer2init() {

    // Setup Timer2 overflow to fire every 8ms (125Hz)
    //   period [sec] = (1 / f_clock [sec]) * prescale * (255-count)
    //                  (1/16000000)  * 1024 * (255-130) = .008 sec

    TCCR2B = 0x00;        // Disable Timer2 while we set it up

    TCNT2  = 130;         // Reset Timer Count  (255-130) = execute ev 125-th T/C clock
    TIFR2  = 0x00;        // Timer2 INT Flag Reg: Clear Timer Overflow Flag
    TIMSK2 = 0x01;        // Timer2 INT Reg: Timer2 Overflow Interrupt Enable
    TCCR2A = 0x00;        // Timer2 Control Reg A: Wave Gen Mode normal
    TCCR2B = 0x05;        // Timer2 Control Reg B: Timer Prescaler set to 1024
}


extern volatile unsigned long msecs = 0;
extern volatile unsigned long refTime = 0;

/*** FUNC
Name:       Timer2 ISR
Function:   Handles the Timer2-overflow interrupt
Description:
Parameters: void
Returns:    void
FUNC ***/

ISR(TIMER2_OVF_vect) {
  static unsigned char count;            // interrupt counter

  //if( (++count & 0x01) == 0 )     // bump the interrupt counter
    ++msecs;              // & count uSec every other time.
  TCNT2 = 256-125;                // reset counter every 125th time (125*4us = 1ms)
  TIFR2 = 0x00;                   // clear timer overflow flag
};


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


///////////////////////////////////////////////////////////////////
//
// SETUP
//


void setup() {
  
  Serial.begin(115200);
  Serial.println("START");
  Serial.print("SMARTCLAMP version: ");
  Serial.println(SMARTCLAMP_VERSION);

  pinMode(SENSOR_A_PIN, INPUT);
  digitalWrite(SENSOR_A_PIN, HIGH);
  attachInterrupt(0, isr1, RISING);

  pinMode(LASER_PIN, OUTPUT);
  digitalWrite(LASER_PIN, HIGH); 

  Timer2init();

}

void loop() {

  // Handling Serial Buffer
  
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

  
  // Operations taken every second
  if (msecs % 1000 == 0 and msecs > 0){

    msecs = 0;
    refTime++;
    
    // light sensors
    unsigned long na = cnta - oldcnta;
    oldcnta = cnta;
    Ia = na*10;
    
    Serial.print("\ttime=");
    Serial.print((int)refTime);
    Serial.print("\tIa=");
    Serial.print((float)Ia/1000);
    Serial.print("\ttemp=");
    Serial.print(getArduinoTemp(),2);
    Serial.print("\tLaserON=");
    Serial.print(laserOn);
    Serial.println("");

    if (laserOn){
      digitalWrite(LASER_PIN, LOW);
      }
      else{
        digitalWrite(LASER_PIN, HIGH);
      }

    
  }
}


// Serial Processing Functions

void processSerialBuffer(){
  if( toupper(serialBuffer[bufferPos]) == 'L'){
    if( toupper(serialBuffer[bufferPos+1]) == 'O'){
      if( toupper(serialBuffer[bufferPos+2]) == 'N'){
        // LON - Laser ON
        laserOn = true;
        Serial.print("Laser On: ");
        Serial.println(laserOn);
      }
      else if( toupper(serialBuffer[bufferPos+2]) == 'F'){
        // LOF - Laser OF
        laserOn = false;
        Serial.print("Laser On: ");
        Serial.println(laserOn);
      }
    }
  }
}
