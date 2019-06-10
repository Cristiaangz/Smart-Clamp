#
#   FILE: smartclamp
#   AUTHOR: Cristian Garcia (Based on turbidostat.py by Christian Wohltat, Stefan Hoffman)
#   DATE: 2019 06 02
#


##################################################
##
##  LIBRARIES AND Initialization
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

logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s',)

homeFolder = os.path.expanduser("~")
logFileFolder = homeFolder + '/Smart-Clamp/logs/'
if not os.path.exists(logFileFolder):
    os.makedirs(logFileFolder)
debug_log = open(logFileFolder + 'debug.log', 'w+')

print("Log Folder: ", logFileFolder, "\n")


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
        self.temp = 0               ## Arduino Temperature
        self.LaserON = False
        self.time = 0               ## Time since started collecting data
        self.refTime = 0            ## Time given by Arduino
        self.verbose = False        ## Prints the readings


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
            self.thread = threading.Thread(target=self.SerialThread)
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


        new_sample_available = False
        self.new_sample_available = False

        self.LogToCSVFile('#time [s]\tIntensity\ttemperature [degree C])\tLaser On\n')
        self.LogToTxtFile('#time [s]\tIntensity\ttemperature [degree C])\tLaser On\n')

        if self.verbose:
            print('Start Time:', datetime.datetime.now().strftime('%H:%M:%S'), "\n")
            print('Time\t\tIa\tTemp\tLON\n')

        self.lock.release()

        while not self.done:
            if self.connected:
                try:
                    response = self.ser.readline()
                    response = response.decode()
                except :
                    print ('except when reading response')
                    self.connected = False
                    self.connecting = True
                    continue

                if len(response) > 1:   # and response[-1] == '\n'

                    if response.find('START') == 0:
                        ## Procedures to do at Start. May be replicated for other comms
                        pass


                    for (var, value) in re.findall(r'([^=\t ]*)=([-0-9\.]+)', response):
                        # find 0 or more (*) strings that start (^) with a tab (\t) and are
                        # followed by one or more (+) numbers from 0-9 ignoring \.

                        if var == 'time':
                            if value != self.refTime:
                                self.new_sample_available = True
                                self.time = self.time + 1
                                self.refTime = long(value)

                        if var == 'Ia':
                            self.Ia = float(value)

                        if var == 'temp':
                            self.temp = float(value)

                        if var == 'LaserON':
                            self.LaserON = float(value)
                if self.new_sample_available:
                    logstring = '%s\t%.2f\t%.0f\t%.0f\n' % (self.time, self.Ia, self.temp, self.LaserON)
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
        'QUIT': quitProg,
        'LON' : LON,
        'LOF' : LOF
    }
    #print(switcher)
    func=switcher.get(input, invalidCmd)
    #print("the function called was", func)
    try:
        return func(object)
    except TypeError:
        print("There was a TypeError when running, func")
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

def invalidCmd(sc):
    print("Invalid command for %s ID: %s\n" % (sc.__name__, sc.ID))

exit = False

def main():
    sc = SmartClamp(1)

    while not exit:
        inp = input(">> ")
        processInput(inp.upper(), sc)

if __name__ == '__main__':
    main()
