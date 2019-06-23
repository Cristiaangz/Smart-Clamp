#
#   FILE: smartclamp
#   AUTHOR: Cristian Garcia (Based on turbidostat.py by Christian Wohltat, Stefan Hoffman)
#   DATE: 2019 06 02
#


##################################################
##
##  LIBRARIES AND Initializationi
##
##########################

import threading
import serial
import serial.tools.list_ports
import sys
from time import sleep
import re
import os
import configparser
import datetime
import string
from pylab import *
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
from scipy.stats import linregress

SCVERSION = 0.10

print("\n\nSTART")
print("SMARTCLAMP.PY VERSION: ",SCVERSION)

CMDlist = [
"Connect: connect to Smart Clamp",
"Disconnect: Disconnect from Smart Clamp",
"LON: Turn on Laser / LED",
"LOF: Turn off Laser / LED",
"SLI: Set Light Intensity",
"V: Toggle verbose output",
"Quit: Close Program" ]

logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s',)

homeFolder = os.path.expanduser("~")
logFileFolder = homeFolder + '/Smart-Clamp/logs/'
if not os.path.exists(logFileFolder):
    os.makedirs(logFileFolder)
debug_log = open(logFileFolder + 'debug.log', 'w+')

print("Log Folder: ", logFileFolder, "\n")

print("LIST OF COMMANDS:")
for cmd in CMDlist:
    print(cmd)


##################################################
##
##  Classes
##
##########################

class SmartClamp:
    def __init__(self, ID):
        self.__name__ = "Smart Clamp"
        self.ID = ID
        self.data_source =  None    ## Serial Address where data is being read from
        self.connected = False
        self.connecting = False
        self.done = False
        self.ser = None             ## Stores the serial connection
        self.threads = 0            ## Number of other than main thread
        self.lock = threading.Lock()## Threading Lock

        #Variables for Arduino
        self.temp_ard = 0               ## Arduino Temperature
        self.time = 0               ## Time since started collecting data
        self.refTime = 0            ## Time given by Arduino
        self.verbose = False        ## Prints the readings

        #Variables for Light Sensor
        self.Ia = 0                 ## Intensity of Sensor A in uW/m2

        #Variables for Light Source
        self.LightOn = False
        self.potentiometer = 128

        #Variables for Gyro
        self.calibrated = threading.Event()
        self.calibrated.clear()

        self.acc_x = 0
        self.acc_y = 0
        self.acc_z = 0
        self.temp_mpu = 0
        self.gyro_x = 0
        self.gyro_y = 0
        self.gyro_z = 0

        #Variables for plotting
        self.times = []
        self.Ias = []
        self.temp_ards = []
        self.LONs = []
        self.acc_xs = []
        self.acc_ys = []
        self.acc_zs = []
        self.temp_mpus = []
        self.gyro_xs = []
        self.gyro_ys = []
        self.gyro_zs = []



    def findSerialPorts(self):
        ## Looks for USB serial devices connected.
        print("Updating Serial Ports")
        self.serialport_list = serial.tools.list_ports.comports()

        if os.name == 'posix':  ## MacOS
            print ("\tmacOS detected")
            self.serialports = [ row[0] for row in self.serialport_list if 'usb' in row[0]]

            if len(self.serialports) > 0:
                self.m_tcPort = self.serialports[0]
                print("\tFound USB serial port: ",self.m_tcPort)
        elif os.name == 'nt':   ## Windows
            print ("\tWindows detected")
            self.serialports = [ row[0] for row in serialport_list if 'COM' in row[0]]
            if len(self.serialports) > 0:
                self.m_tcPort = self.serialports[0]
                print("\tFound USB serial port: ",self.m_tcPort)

    def checkConnect(self):
        print("\nChecking Connection")
        if not self.connected and not self.connecting:
            print("\tNot connected")
            try:
                self.data_source = self.m_tcPort
                self.startSerialSession()
            except AttributeError:
                print("\tNo valid USB connections were found")
            except:
                print("Something went wrong when starting the Serial Session")
        if self.ser:
            print ("\nConnection successful, Threads Starting\n")
            self.serialThread.start()

        else:
            print ("\nConnection unsuccessful\n")


    def startSerialSession(self):
        print("\tStarting Serial Session")
        self.connect( self.data_source )
        self.connecting = False

    def connect(self, data_source):
        print("\tTrying to connect to ", data_source)

        # now connect with correct speed
        self.ser = serial.Serial(data_source, 115200, timeout=0)
        self.ser.flush()

        if self.ser:
            print("\tConnected to ", data_source)
            self.connected = True
            self.connecting = False
            self.done = False

            self.logFilePath = logFileFolder + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.txt'

            self.logFilePath_csv = logFileFolder + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.csv'
            self.logfile_csv = open(self.logFilePath_csv, 'a+')
            self.serialThread = threading.Thread(target=self.SerialThread, name='Serial Stream')
            self.serialThread.setDaemon(True)

    def closeSerialSession(self):
        self.done = True
        sleep(0.2)
        self.connecting = False
        self.disconnect()

    def disconnect(self):
        if self.logfile:
            self.logfile.close()
        self.logfile_csv.close()
        self.connected = False
        if self.ser:
            self.ser.close()
            self.ser = None

        ### Writing Logs

    def SerialThread(self):
        if self.threads > 0:
            return
        self.lock.acquire()
        self.threads += 1
        #print ('nthreads ', self.threads)

        self.xs = []
        self.ys = []

        temp_response = ""
        response = ""

        new_sample_available = False
        self.new_sample_available = False

        self.LogToCSVFile('Time [s]\tIntensity A\tLaser On\tAcX\tAcY\tAcZ\tGyX\tGyY\tGyZ\tArd Temp [C])\tMPU Temp [C]\n')
        #self.LogToTxtFile('Time [s]\tIntensity A\tLaser On\tAcX\tAcY\tAcZ\tGyX\tGyY\tGyZ\tArd Temp [C])\tMPU Temp [C]\n')

        if self.verbose:
            print('Start Time:', datetime.datetime.now().strftime('%H:%M:%S'), "\n")
            print('Time [s]\tIntensity A\tLaser On\tAcX\tAcY\tAcZ\tGyX\tGyY\tGyZ\tArd Temp [C])\tMPU Temp [C]\n')

        self.lock.release()

        while not self.done:
            if self.connected:
                try:
                    temp_response += self.ser.readline().decode()
                    if temp_response[-3] == "$":
                        response = temp_response
                        temp_response = "";
                except IndexError:
                    continue
                except :
                    print ('except when reading response')
                    self.connected = False
                    self.connecting = True
                    continue

                if len(response) > 1 and response[-3] == '$':
                    response = response[:-3] + response[-2:-1]
                    #print(response)
                    #print(response[-3])

                    if response.find('START') == 0:
                        ## Procedures to do at Start. May be replicated for other comms
                        print("\nCalibrating")
                        pass
                    if response.find('CALIBRATION DONE') == 0:
                        ## Procedures to do at Start. May be replicated for other comms
                        print("\nCalibration Done")
                        self.calibrated.set()
                        pass

                    for (var, value) in re.findall(r'([^=\t ]*)=([-0-9\.]+)', response):
                        # find 0 or more (*) strings that start (^) with a tab (\t) and are
                        # followed by one or more (+) numbers from 0-9 ignoring \.



                        if var == 'time':
                            if value != self.time:
                                self.new_sample_available = True
                                self.time = self.time + 1
                                self.refTime = long(value)

                        elif var == 'Ia':
                            self.Ia = float(value)

                        elif var == 'temp_ard':
                            self.temp_ard = float(value)

                        elif var == 'LaserON':
                            self.LightOn = float(value)

                        # Check if gyro values

                        elif var == 'acc_x':
                            self.acc_x = float(value)

                        elif var == 'acc_y':
                            self.acc_y = float(value)

                        elif var == 'acc_z':
                            self.acc_z = float(value)

                        elif var == 'gyro_x':
                            self.gyro_x = float(value)

                        elif var == 'gyro_y':
                            self.gyro_y = float(value)

                        elif var == 'gyro_z':
                            self.gyro_z = float(value)

                        elif var == 'temp_mpu':
                            self.temp_mpu = float(value)

                    response = ""


                if self.new_sample_available:

                #Update data list
                    if self.refTime > 0:    ##Ignore first two unstable readings
                        self.times.append(self.refTime)
                        self.Ias.append(self.Ia)
                        self.temp_ards.append(self.temp_ard)
                        self.LONs.append(self.LightOn)
                        self.acc_xs.append(self.acc_x)
                        self.acc_ys.append(self.acc_y)
                        self.acc_zs.append(self.acc_z)
                        self.temp_mpus.append(self.temp_mpu)
                        self.gyro_xs.append(self.gyro_x)
                        self.gyro_ys.append(self.gyro_y)
                        self.gyro_zs.append(self.gyro_z)

                    logstring = '{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(self.time, self.Ia, self.LightOn, self.acc_x, self.acc_y, self.acc_z, self.gyro_x, self.gyro_y, self.gyro_z, self.temp_ard, self.temp_mpu)

                    if self.verbose:
                        print (datetime.datetime.now().strftime('%H:%M:%S'), logstring, sep=" | ")


                    self.LogToCSVFile(logstring)

                    self.lock.acquire()
                    self.logfile = open(self.logFilePath, 'w+')                 # Change to w+ to constantly overwrite
                    self.LogToTxtFile(logstring)
                    self.logfile.close()
                    self.lock.release()
                    self.new_sample_available = False
                #time.sleep(0.5)



    def LogToFile(self, f, s):
        f.write(s)

        try:
            f.flush()
        # ignore and flush later ('magically' locked file, e.g. by excel import)
        except IOError:
            if e.errno != 13:
                debug_log.write(str(e.errno) + '\n')

    def LogToTxtFile(self, s):
        self.LogToFile( self.logfile, s)

    def LogToCSVFile(self, s):
        self.LogToFile( self.logfile_csv, s)

    def plotThread(self):
        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(1,1,1)

        self.ani = animation.FuncAnimation(self.fig, self.animate, interval=1000)

        #Live Plot Labels
        plt.xlabel("Time [s]")
        plt.ylabel("Irradience [W/m^2]")
        plt.title("Light Sensor Live Plot")
        plt.legend()

        plt.show()

    def animate(self, label):
        # graph_data = open(self.logFilePath,'r').read()
        # lines = graph_data.split('\n')
        # xs = []
        # ys = []
        # for line in lines:
        #     if len(line) > 1:
        #         time, Ia, LON, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, temp_ard, temp_mp = line.split('\t')
        #         xs.append(float(timte))
        #         ys.append(float(Ia))
        self.ax1.clear()
        self.ax1.plot(self.times, self.Ias, label="irradience")

    def brightTest(self, timeInt=20, numLevels = 8):
        print("Brightness Test Started")
        level = 1
        if self.connected and self.LightOn and self.refTime < timeInt:
            self.ser.write('LOF\n'.encode())
            self.LightOn = False
        print("Test waiting for Calibration to Finish")
        self.calibrated.wait()
        print("Test starting")
        while self.connected:
            if self.time > ((level * timeInt) - 2):
                self.ser.write('LON\n'.encode())
                print('Light Turned On')

                if level > 1:
                    self.potentiometer -= 1
                cmd = "SLI "+ str(self.potentiometer)+"\n"
                self.ser.write(cmd.encode())
                print("Potentiometer Level: ", self.potentiometer)

                level += 1

                if level == (numLevels + 1):
                    self.ser.write('LOF\n'.encode())
                    self.LightOn = False
                    self.closeSerialSession()
        print("Test Finished")


##################################################
##
##  Main Loop Functions
##
##########################

def processInput(input, object=None):
    #print("The Input was :", input)
    switcher={
        'CONNECT': connectToSC ,
        'DISCONNECT': disconnectFromSC,
        'D' : disconnectFromSC,
        'QUIT': quitProg,
        'Q': quitProg,
        'LON' : LON,
        'LOF' : LOF,
        'V' : verbose,
        'SLI' : setLightIntensity,
        'PLOT' : plot,
        'P' : plot,
        'TEST' : test
    }
    #print(switcher)
    func=switcher.get(input, invalidCmd)
    #print("the function called was", func)
    try:
        return func(object)
    except TypeError:
        print("There was a TypeError when running", func)
        return

def connectToSC(sc):
    sc.findSerialPorts()
    sc.checkConnect()

def test(sc):
    try:
        timeInt = int(input("Set Time Interval Between Levels [seconds]: "))
        numLevels = int(input("Set Number of Levels Testes [Min 2]: "))
        if not sc.connected:
            sc.findSerialPorts()
            sc.checkConnect()

        testThread = threading.Thread(target=sc.brightTest, args=(timeInt, numLevels), name='Brightness Test')
        testThread.setDaemon(True)
        if sc.connected:
            testThread.start()
            print('Test Thread Started')
            sc.plotThread()
    except:
        print("Something went wrong with Brightness Test")


def disconnectFromSC(sc):
    sc.closeSerialSession()

def quitProg(sc):
    if sc.ser:
        sc.closeSerialSession()
    sys.exit()

def LON(sc):
    try:
        sc.ser.write('LON\n'.encode())
    except AttributeError:
        print("Not connected to Smart Clamp (>> connect)")

def LOF(sc):
    try:
        sc.ser.write('LOF\n'.encode())
    except AttributeError:
        print("Not connected to Smart Clamp (>> connect)")

def verbose(sc):
    try:
        sc.verbose = not(sc.verbose)
        print("verbose is", sc.verbose)
    except AttributeError:
        print("Not connected to Smart Clamp (>> connect)")

def setLightIntensity(sc):
    while True:
        try:
            intensity = int(input("Set intensity to [0-128]: "))
        except ValueError:
            print("Please enter an integer from 0 to 128")
            continue
        try:
            if (0 <= intensity <= 128):
                cmd = "SLI "+ str(intensity)+"\n"
                sc.ser.write(cmd.encode())
                sc.potentiometer = cmd
                break
        except AttributeError:
            print("Not connected to Smart Clamp (>> connect)")
            break

def plot(sc):
    sc.plotThread()

def invalidCmd(sc):
    print("Invalid command for %s ID: %s\n" % (sc.__name__, sc.ID))

exit = False

##################################################
##
##  Main Loop
##
##########################

def main():
    sc = SmartClamp(1)

    while not exit:
        inp = input("\n>> ")
        processInput(inp.upper(), sc)

if __name__ == '__main__':
    main()
