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
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from scipy.stats import linregress

SCVERSION = 0.03

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
        self.Ia = 0                 ## Intensity of Sensor A in uW/m2
        self.temp_ard = 0               ## Arduino Temperature
        self.LaserON = False
        self.time = 0               ## Time since started collecting data
        self.refTime = 0            ## Time given by Arduino
        self.verbose = False        ## Prints the readings

        #Variables for Gyro
        self.acc_x = 0
        self.acc_y = 0
        self.acc_z = 0
        self.temp_mpu = 0
        self.gyro_x = 0
        self.gyro_y = 0
        self.gyro_z = 0



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
            print ("\nConnection successful, Thread Starting\n")
            self.thread.start()
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

            logFilePath = logFileFolder + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.txt'
            self.logfile = open(logFilePath, 'a+') # Change to w+ to constantly overwrite

            logFilePath_csv = logFileFolder + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.csv'
            self.logfile_csv = open(logFilePath_csv, 'a+')
            self.thread = threading.Thread(target=self.SerialThread, name='Serial Stream')
            self.thread.setDaemon(True)

    def closeSerialSession(self):
        self.done = True
        sleep(0.2)
        self.connecting = False
        self.disconnect()

    def disconnect(self):
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

        temp_response = ""
        response = ""

        new_sample_available = False
        self.new_sample_available = False

        self.LogToCSVFile('Time [s]\tIntensity A\tLaser On\tAcX\tAcY\tAcZ\tGyX\tGyY\tGyZ\tArd Temp [C])\tMPU Temp [C]\n')
        self.LogToTxtFile('Time [s]\tIntensity A\tLaser On\tAcX\tAcY\tAcZ\tGyX\tGyY\tGyZ\tArd Temp [C])\tMPU Temp [C]\n')

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

                    for (var, value) in re.findall(r'([^=\t ]*)=([-0-9\.]+)', response):
                        # find 0 or more (*) strings that start (^) with a tab (\t) and are
                        # followed by one or more (+) numbers from 0-9 ignoring \.



                        if var == 'time':
                            if value != self.refTime:
                                self.new_sample_available = True
                                self.time = self.time + 1
                                self.refTime = long(value)

                        elif var == 'Ia':
                            self.Ia = float(value)

                        elif var == 'temp_ard':
                            self.temp_ard = float(value)

                        elif var == 'LaserON':
                            self.LaserON = float(value)

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
                    logstring = '{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(self.time, self.Ia, self.LaserON, self.acc_x, self.acc_y, self.acc_z, self.gyro_x, self.gyro_y, self.gyro_z, self.temp_ard, self.temp_mpu)

                    if self.verbose:
                        print (datetime.datetime.now().strftime('%H:%M:%S'), logstring, sep=" | ")
                    self.LogToCSVFile(logstring)
                    self.LogToTxtFile(logstring)
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

##################################################
##
##  Main Loop
##
##########################

def processInput(input, object=None):
    #print("The Input was :", input)
    switcher={
        'CONNECT': connectToSC ,
        'DISCONNECT': disconnectFromSC,
        'D' : disconnectFromSC,
        'QUIT': quitProg,
        'LON' : LON,
        'LOF' : LOF,
        'V' : verbose,
        'SLI' : setLightIntensity
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
                intensity = -1
                break
        except AttributeError:
            print("Not connected to Smart Clamp (>> connect)")
            break



def invalidCmd(sc):
    print("Invalid command for %s ID: %s\n" % (sc.__name__, sc.ID))

exit = False

def main():
    sc = SmartClamp(1)

    while not exit:
        inp = input("\n>> ")
        processInput(inp.upper(), sc)

if __name__ == '__main__':
    main()
