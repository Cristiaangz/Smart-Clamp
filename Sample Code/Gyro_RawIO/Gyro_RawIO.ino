// MPU-6050 Short Example Sketch
// By Arduino User JohnChi
// August 17, 2014
// Public Domain
#include<Wire.h>
const int MPU_addr=0x68;  // I2C address of the MPU-6050
int16_t AcX,AcY,AcZ,Tmp,GyX,GyY,GyZ;


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
extern volatile float refTime = 0;


ISR(TIMER2_OVF_vect) {
  static unsigned char count;            // interrupt counter

  //if( (++count & 0x01) == 0 )     // bump the interrupt counter
    ++msecs;              // & count uSec every other time.
  TCNT2 = 256-125;                // reset counter every 125th time (125*4us = 1ms)
  TIFR2 = 0x00;                   // clear timer overflow flag
};





void setup(){
  Wire.begin();
  Wire.beginTransmission(MPU_addr);
  Wire.write(0x6B);  // PWR_MGMT_1 register
  Wire.write(0);     // set to zero (wakes up the MPU-6050)
  Wire.endTransmission(true);
  Serial.begin(115200);

  Timer2init();
}
void loop(){

  if (msecs % 100 == 0 and msecs > 0){

    msecs = 0;
    refTime = refTime + 0.1;
    
    Wire.beginTransmission(MPU_addr);
    Wire.write(0x3B);  // starting with register 0x3B (ACCEL_XOUT_H)
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_addr,14,true);  // request a total of 14 registers
    AcX=Wire.read()<<8|Wire.read();  // 0x3B (ACCEL_XOUT_H) & 0x3C (ACCEL_XOUT_L)    
    AcY=Wire.read()<<8|Wire.read();  // 0x3D (ACCEL_YOUT_H) & 0x3E (ACCEL_YOUT_L)
    AcZ=Wire.read()<<8|Wire.read();  // 0x3F (ACCEL_ZOUT_H) & 0x40 (ACCEL_ZOUT_L)
    Tmp=Wire.read()<<8|Wire.read();  // 0x41 (TEMP_OUT_H) & 0x42 (TEMP_OUT_L)
    GyX=Wire.read()<<8|Wire.read();  // 0x43 (GYRO_XOUT_H) & 0x44 (GYRO_XOUT_L)
    GyY=Wire.read()<<8|Wire.read();  // 0x45 (GYRO_YOUT_H) & 0x46 (GYRO_YOUT_L)
    GyZ=Wire.read()<<8|Wire.read();  // 0x47 (GYRO_ZOUT_H) & 0x48 (GYRO_ZOUT_L)
    //Serial.print("\ttime=");
    Serial.print("\t");  
    Serial.print((float)refTime);
    //Serial.print("\tAcX="); 
    Serial.print("\t"); 
    Serial.print(AcX);
    //Serial.print("\tAcY="); 
    Serial.print("\t"); 
    Serial.print(AcY);
    //Serial.print("\tAcZ="); 
    Serial.print("\t"); 
    Serial.print(AcZ);
    //Serial.print("\tGtemp="); 
    Serial.print("\t"); 
    Serial.print(Tmp/340.00+36.53);  //equation for temperature in degrees C from datasheet
    //Serial.print("\tGyX="); 
    Serial.print("\t"); 
    Serial.print(GyX);
    //Serial.print("\tGyY="); 
    Serial.print("\t"); 
    Serial.print(GyY);
    //Serial.print("\tGyZ="); 
    Serial.print("\t"); 
    Serial.println(GyZ);
  }
}
