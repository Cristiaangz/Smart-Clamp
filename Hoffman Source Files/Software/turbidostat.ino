/*
 *    FILE: turbidostat.ino
 *  AUTHOR: Christian Wohltat, Stefan Hoffman
 *    DATE: 2016 05 09
 *
 *  PURPOSE:
 */
#define TURBIDOSTAT_VERSION  "0.2"
#define NO_PORTB_PINCHANGES // to indicate that port b will not be used for pin change interrupts
#define NO_PORTC_PINCHANGES // to indicate that port c will not be used for pin change interrupts

#define PINMODE
#define FLASH
#include <PinChangeInt.h>
#include <EEPROM.h>
#include <avr/eeprom.h>

#define SENSOR_A_PIN  2
#define SENSOR_B_PIN  3
#define HALLPIN       4
#define PUMPPIN       5
#define STIRRERPIN    6
#define AIRPUMPPIN    10

#define EEPROM_OFFSET 0
#define EEPROM_TARGET_I                (0*sizeof(unsigned long))
#define EEPROM_I_0                     (1*sizeof(unsigned long))
#define EEPROM_PUMP_MODE               (2*sizeof(unsigned long))
#define EEPROM_PUMP_POWER              (3*sizeof(unsigned long))
#define EEPROM_AIRPUMP_POWER           (4*sizeof(unsigned long))
#define EEPROM_PUMP_PULS_DURATION      (5*sizeof(unsigned long))
#define EEPROM_PUMP_PULS_WAIT          (6*sizeof(unsigned long))
#define EEPROM_STIRRER_RPM             (7*sizeof(unsigned long))

volatile unsigned long cnta = 0;
volatile unsigned long cntb = 0;
volatile unsigned long stirrerIntCnt = 0;
unsigned long oldcnta = 0;
unsigned long oldcntb = 0;
unsigned long t = 0;

#define SERIAL_BUFFER_LEN 128
char serialBuffer[SERIAL_BUFFER_LEN];
unsigned short bufferEnd = 0;
unsigned short bufferPos = 0;

// stirrer parameter
byte stirrerOut = 30;
unsigned long stirrerRPM = 800;  // in Hz

// OD measurement parameter
float targetOD = 1;
float OD = 0;
unsigned long Ia = 0;         // current intensity of sensor A in uW/m2
unsigned long Ib = 0;         // current intensity of sensor B in uW/m2
unsigned long I = 0;         // current intensity in uW/m2
unsigned long targetI = 0;   // target intensity in uW/m2
unsigned long I_0 = 0;       // zero intensity in uW/m2

// pump parameter
unsigned long pumpMode = 0;
unsigned long pumpPower = 255;
unsigned long airpumpPower = 0;
unsigned long pumpPulsDuration = 100;  // in ms
unsigned long pumpPulsWait = 5000;     // in ms
byte thresholdCnt = 0;
#define NTIMESTHRESHOLD  3


//////////////////////////////
//
// PROTOTYPES
//
//////////////////////////////
void            processSerialBuffer();
unsigned long   getSerialIntArgument();
void            setPwmFrequency(int pin, int divisor);
double          getArduinoTemp(void);
void            setupADC();


// INTERRUPT ROUTINES
void irq1()
{
  cnta++;
}

void irq2()
{
  cntb++;
}

void irq3()
{
  stirrerIntCnt++;
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


void eeprom_save(){
  eeprom_write_block((const void*)&targetI,           (void*)EEPROM_TARGET_I + EEPROM_OFFSET,           sizeof(unsigned long));
  eeprom_write_block((const void*)&I_0,               (void*)EEPROM_I_0 + EEPROM_OFFSET,                sizeof(unsigned long));
  eeprom_write_block((const void*)&stirrerRPM,        (void*)EEPROM_STIRRER_RPM + EEPROM_OFFSET,        sizeof(unsigned long));
  eeprom_write_block((const void*)&pumpPulsDuration,  (void*)EEPROM_PUMP_PULS_DURATION + EEPROM_OFFSET, sizeof(unsigned long));
  eeprom_write_block((const void*)&pumpPulsWait,      (void*)EEPROM_PUMP_PULS_WAIT + EEPROM_OFFSET,     sizeof(unsigned long));
  eeprom_write_block((const void*)&pumpMode,          (void*)EEPROM_PUMP_MODE + EEPROM_OFFSET,          sizeof(unsigned long));
  eeprom_write_block((const void*)&pumpPower,         (void*)EEPROM_PUMP_POWER + EEPROM_OFFSET,         sizeof(unsigned long));
  eeprom_write_block((const void*)&airpumpPower,      (void*)EEPROM_AIRPUMP_POWER + EEPROM_OFFSET,      sizeof(unsigned long));
}

void eeprom_load(){
  // load parameter from eeprom
  eeprom_read_block(&targetI,           (const void*)EEPROM_TARGET_I + EEPROM_OFFSET,           sizeof(unsigned long));
  eeprom_read_block(&I_0,               (const void*)EEPROM_I_0 + EEPROM_OFFSET,                sizeof(unsigned long));
  targetOD = pow(10, (float)I_0/targetI);

  eeprom_read_block(&stirrerRPM,        (const void*)EEPROM_STIRRER_RPM + EEPROM_OFFSET,        sizeof(unsigned long));
  eeprom_read_block(&pumpPulsDuration,  (const void*)EEPROM_PUMP_PULS_DURATION + EEPROM_OFFSET, sizeof(unsigned long));
  eeprom_read_block(&pumpPulsWait,      (const void*)EEPROM_PUMP_PULS_WAIT + EEPROM_OFFSET,     sizeof(unsigned long));
  eeprom_read_block(&pumpMode,          (const void*)EEPROM_PUMP_MODE + EEPROM_OFFSET,          sizeof(unsigned long));
  eeprom_read_block(&pumpPower,         (const void*)EEPROM_PUMP_POWER + EEPROM_OFFSET,         sizeof(unsigned long));
  eeprom_read_block(&airpumpPower,      (const void*)EEPROM_AIRPUMP_POWER + EEPROM_OFFSET,      sizeof(unsigned long));

  Serial.print("targetI: ");
  Serial.println(targetI);
  Serial.print("I_0: ");
  Serial.println(I_0);
  Serial.print("stirrerRPM: ");
  Serial.println(stirrerRPM);
  Serial.print("pumpPulsDuration: ");
  Serial.println(pumpPulsDuration);
  Serial.print("pumpPulsWait: ");
  Serial.println(pumpPulsWait);
  Serial.print("pumpMode: ");
  Serial.println(pumpMode);
  Serial.print("pumpPower: ");
  Serial.println(pumpPower);
  Serial.print("airpumpPower: ");
  Serial.println(airpumpPower);


  // set default values if eeprom values are "undefined" and save it to eeprom
  // this is propably only done once when eeprom is empty
  if (stirrerRPM > 3000){
    stirrerRPM = 800;
    eeprom_write_block(&stirrerRPM,       (void*)EEPROM_STIRRER_RPM + EEPROM_OFFSET,          sizeof(unsigned long));
  }
  if (pumpPulsDuration > 1000000){
    pumpPulsDuration = 100;
    eeprom_write_block(&pumpPulsDuration, (void*)EEPROM_PUMP_PULS_DURATION + EEPROM_OFFSET,   sizeof(unsigned long));
  }
  if (pumpPulsWait > 10000000){
    pumpPulsWait = 5000;
    eeprom_write_block(&pumpPulsWait,     (void*)EEPROM_PUMP_PULS_WAIT + EEPROM_OFFSET,       sizeof(unsigned long));
  }
  // if (pumpMode == 0){
  //   pumpMode = 0;
  // }
  if (pumpPower > 255){
    pumpPower = 255;
    eeprom_write_block(&pumpPower,        (void*)EEPROM_PUMP_POWER + EEPROM_OFFSET,           sizeof(unsigned long));
  }
  // if (airpumpPower == 0){
  //   airpumpPower = 0;
  // }
}

///////////////////////////////////////////////////////////////////
//
// SETUP
//
void setup()
{
  Serial.begin(115200);
  Serial.println("START");
  Serial.print("version: ");
  Serial.println(TURBIDOSTAT_VERSION);

  eeprom_load();

  pinMode(12, OUTPUT);
  analogWrite(12, LOW);

  pinMode(SENSOR_A_PIN, INPUT);
  digitalWrite(SENSOR_A_PIN, HIGH);
  attachInterrupt(0, irq1, RISING);

  pinMode(SENSOR_B_PIN, INPUT);
  digitalWrite(SENSOR_B_PIN, HIGH);
  attachInterrupt(1, irq2, RISING);

  pinMode(HALLPIN, INPUT);
  digitalWrite(HALLPIN, HIGH);
  // software interrupt for hall sensor
  PCintPort::attachInterrupt(HALLPIN, &irq3, FALLING);  // add more attachInterrupt code as required

  pinMode(PUMPPIN, OUTPUT);
  analogWrite(PUMPPIN, 0);

  pinMode(AIRPUMPPIN, OUTPUT);
  analogWrite(AIRPUMPPIN, airpumpPower);

  pinMode(STIRRERPIN, OUTPUT);
  analogWrite(STIRRERPIN, stirrerOut);
  #define PWM_DEVISOR 8
  #define TIME_FACTOR (64/PWM_DEVISOR)
  setPwmFrequency(STIRRERPIN, PWM_DEVISOR);
  setPwmFrequency(AIRPUMPPIN, PWM_DEVISOR);

  Timer2init();


}




///////////////////////////////////////////////////////////////////
//
// MAIN LOOP
//
void loop()
{
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

  if (msecs % 1000 == 0){
    // light sensors
    unsigned long na = cnta - oldcnta;
    unsigned long nb = cntb - oldcntb;
    oldcnta = cnta;
    oldcntb = cntb;
    Ia = na*10;
    Ib = nb*10;
    I=Ia*1000/Ib;
    OD = -(log10(I)-log10(I_0));


    // print serial output
    Serial.print("\tt=");
    Serial.print(msecs);
    Serial.print("\tI=");
    Serial.print((float)I);
    Serial.print("\tIa=");
    Serial.print((float)Ia/1000);
    Serial.print("\tIb=");
    Serial.print((float)Ib/1000);
    Serial.print("\tOD=");
    Serial.print(OD);
    Serial.print("\tlog10(I)=");
    Serial.print(log10(I));
    Serial.print("\tlog10(I_0)=");
    Serial.print(log10(I_0));
    Serial.print("\tf_stirrer=");
    Serial.print((stirrerIntCnt*60));
    Serial.print("\ttemp=");
    Serial.print(getArduinoTemp(),2);
    Serial.println("");

    ////////////////////////
    // control
    ////////////////////////
    // stirrer
    if(stirrerIntCnt*60 < stirrerRPM){
      stirrerOut += 1;
    }
    else{
      stirrerOut -= 1;
    }
    analogWrite(STIRRERPIN, stirrerOut);


    stirrerIntCnt = 0;

  }

  // Pump
  if((targetI != 0) && (pumpMode == 0)){
    static unsigned long lastPulsTime = 0;
    static boolean pumppin = false;

    // hello future me, please comment and find meaningful names
    if( targetI > I ){
      if((pumppin == false) && (lastPulsTime + pumpPulsWait < msecs)){
        thresholdCnt++;
        if(thresholdCnt >= NTIMESTHRESHOLD){
          thresholdCnt = NTIMESTHRESHOLD; // to prevent overflow
          analogWrite(PUMPPIN, pumpPower);
          pumppin = true;
          lastPulsTime = msecs;
          Serial.println("Pump On");
        }
      }
    }
    else{
      thresholdCnt = 0;
    }
    if( (pumppin == true) && (lastPulsTime + pumpPulsDuration < msecs)){

      analogWrite(PUMPPIN, 0);
      pumppin = false;
      Serial.println("Pump Off");
    }
  }
}


void processSerialBuffer(){
  if( toupper(serialBuffer[bufferPos]) == 'S'){
    if( toupper(serialBuffer[bufferPos+1]) == 'A'){
      if( toupper(serialBuffer[bufferPos+2]) == 'P'){
        // SAP - Set Airpump Power
        bufferPos += 3;
        airpumpPower = getSerialIntArgument();
        eeprom_write_block(&airpumpPower,     (void*)EEPROM_AIRPUMP_POWER + EEPROM_OFFSET,       sizeof(unsigned long));
        analogWrite(AIRPUMPPIN, airpumpPower);
        Serial.print("airpumpPower: ");
        Serial.println(airpumpPower);
      }
    }
    if( toupper(serialBuffer[bufferPos+1]) == 'I'){
      if( toupper(serialBuffer[bufferPos+2]) == '0'){
        // SI0 - Set I_0 ( intensity of clear solution )
        I_0 = I;
        eeprom_write_block(&I_0,     (void*)EEPROM_I_0 + EEPROM_OFFSET,       sizeof(unsigned long));
        targetI = I_0*pow(10, -targetOD);
        Serial.print("I_0: ");
        Serial.println(I_0);
      }
    }
    if( toupper(serialBuffer[bufferPos+1]) == 'M'){
      if( toupper(serialBuffer[bufferPos+2]) == 'P'){
        // SOD - Set Manual Pump
        bufferPos += 3;
        if(getSerialIntArgument()){
          analogWrite(PUMPPIN, pumpPower);
          Serial.println("Manual Pump On");
        }
        else{
          analogWrite(PUMPPIN, 0);
          Serial.println("Manual Pump Off");
        }
      }
    }
    if( toupper(serialBuffer[bufferPos+1]) == 'O'){
      if( toupper(serialBuffer[bufferPos+2]) == 'D'){
        // SOD - Set Optical Density
        bufferPos += 3;
        targetOD = getSerialFloatArgument();
        targetI = I_0*pow(10, -targetOD);
        eeprom_write_block(&targetI,     (void*)EEPROM_TARGET_I + EEPROM_OFFSET,       sizeof(unsigned long));
        Serial.print("targetOD: ");
        Serial.print(targetOD);
        Serial.print(", targetI: ");
        Serial.println(targetI);
      }
    }
    if( toupper(serialBuffer[bufferPos+1]) == 'P'){
      if( toupper(serialBuffer[bufferPos+2]) == 'D'){
        // SPD - Set Pump puls Duration
        bufferPos += 3;
        pumpPulsDuration = getSerialIntArgument();
        eeprom_write_block(&pumpPulsDuration,     (void*)EEPROM_PUMP_PULS_DURATION + EEPROM_OFFSET,       sizeof(unsigned long));
        Serial.print("pumpPulsDuration: ");
        Serial.println(pumpPulsDuration);
      }
      if( toupper(serialBuffer[bufferPos+2]) == 'M'){
        // SPM - Set Pump Mode
        bufferPos += 3;
        pumpMode = getSerialIntArgument();
        eeprom_write_block(&pumpMode,     (void*)EEPROM_PUMP_MODE + EEPROM_OFFSET,       sizeof(unsigned long));
        Serial.print("pumpMode: ");
        Serial.println(pumpMode);
      }
      if( toupper(serialBuffer[bufferPos+2]) == 'P'){
        // SPP - Set Pump Power
        bufferPos += 3;
        pumpPower = getSerialIntArgument();
        eeprom_write_block(&pumpPower,     (void*)EEPROM_PUMP_POWER + EEPROM_OFFSET,       sizeof(unsigned long));
        Serial.print("pumpPower: ");
        Serial.println(pumpPower);
      }
      if( toupper(serialBuffer[bufferPos+2]) == 'W'){
        // SPW - Set Pump puls Wait
        bufferPos += 3;
        pumpPulsWait = getSerialIntArgument();
        eeprom_write_block(&pumpPulsWait,     (void*)EEPROM_PUMP_PULS_WAIT + EEPROM_OFFSET,       sizeof(unsigned long));
        Serial.print("pumpPulsWait: ");
        Serial.println(pumpPulsWait);
      }
    }
    if( toupper(serialBuffer[bufferPos+1]) == 'S'){
      if( toupper(serialBuffer[bufferPos+2]) == 'S'){
        // SSS - Set Stirrer Speed
        bufferPos += 3;
        stirrerRPM = getSerialIntArgument();
        eeprom_write_block(&stirrerRPM,     (void*)EEPROM_STIRRER_RPM + EEPROM_OFFSET,       sizeof(unsigned long));
      }
    }
    if( toupper(serialBuffer[bufferPos+1]) == 'T'){
        // ST - Set Time
        bufferPos += 2;
        unsigned long new_msecs = getSerialIntArgument();
        msecs = new_msecs;
        Serial.print("_st: ");
        Serial.println(msecs);
    }
  }
}

///////////////////////////////////////////////////////////////////
unsigned long getSerialIntArgument(){
  return atol(serialBuffer+(bufferPos+1) );
}

///////////////////////////////////////////////////////////////////
float getSerialFloatArgument(){
  return atof(serialBuffer+(bufferPos+1) );
}


///////////////////////////////////////////////////////////////////
void setPwmFrequency(int pin, int divisor) {
  byte mode;
  if(pin == 5 || pin == 6 || pin == 9 || pin == 10) {
    switch(divisor) {
      case 1: mode = 0x01; break;
      case 8: mode = 0x02; break;
      case 64: mode = 0x03; break;
      case 256: mode = 0x04; break;
      case 1024: mode = 0x05; break;
      default: return;
    }
    if(pin == 5 || pin == 6) {
      TCCR0B = TCCR0B & 0b11111000 | mode;
    } else {
      TCCR1B = TCCR1B & 0b11111000 | mode;
    }
  } else if(pin == 3 || pin == 11) {
    switch(divisor) {
      case    1: mode = 0x01; break;
      case    8: mode = 0x02; break;
      case   32: mode = 0x03; break;
      case   64: mode = 0x04; break;
      case  128: mode = 0x05; break;
      case  256: mode = 0x06; break;
      case 1024: mode = 0x07; break;
      default: return;
    }
    TCCR2B = TCCR2B & 0b11111000 | mode;
  }
}

//////////////////////////////////////////////////////////////////////
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
// END OF FILE
