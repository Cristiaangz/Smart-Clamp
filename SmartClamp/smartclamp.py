#
#   FILE: smartclamp
#   AUTHOR: Cristian Garcia (Based on turbidostat.py by Christian Wohltat, Stefan Hoffman)
#   DATE: 2019 06 02
#

##################################################
##
##  LIBRARIES AND DECLARATIONS
##
##########################

import wx
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

SCVERSION = 0.02

print("\n\nSTART")
print("SMARTCLAMP.PY VERSION: ",SCVERSION)


homeFolder = os.path.expanduser("~")
logFileFolder = homeFolder + '/Smart-Clamp/logs/'
if not os.path.exists(logFileFolder):
    os.makedirs(logFileFolder)
debug_log = open(logFileFolder + 'debug.log', 'w+')

print("Log Folder: ", logFileFolder, "\n")

class SmartClamp:
    def __init__(self, ID):
        self.ID = ID
        self.data_source =  None
        self.connected = False
        self.connecting = False
        self.ser = None
        self.done = False
        self.threads = 0
        self.Ia = 0
        #self.oldIa = 0
        self.temp = 0
        self.LaserON = False
        self.time = 0


    def updateSerialPorts(self):
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
            self.data_source = self.m_tcPort
            self.startSerialSession()
        if self.ser:
            print ("\nConnection successful\n")
            self.SerialProcessing()

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
            #thread.start_new_thread(self.SerialThread, ()) #Needs translation from Thread to Threading Lib

        ### Writing Logs

    def SerialProcessing(self):
        # if self.threads > 0:
        #     return
        #
        # self.threads += 1
        # new_sample_available = False
        # response = ''
        response = ''
        self.new_sample_available = True

        self.LogToCSVFile('#time [s]\tIntensity\ttemperature [degree C])\tLaser On\n')
        self.LogToTxtFile('#time [s]\tIntensity\ttemperature [degree C])\tLaser On\n')
        print('Start Time:', datetime.datetime.now().strftime('%H:%M:%S'), "\n")
        print('Time\tIa\tTemp\tLON\n')

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
                            if (value != self.time):
                                self.new_sample_available = True
                                self.time = self.time + 1

                        if var == 'Ia':
                            self.Ia = float(value)

                        if var == 'temp':
                            self.temp = float(value)

                        if var == 'LaserON':
                            self.LaserON = float(value)
                if self.new_sample_available:
                    logstring = '%s\t%.2f\t%.0f\t%.0f\n' % (self.time, self.Ia, self.temp, self.LaserON)
                    print (logstring)
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

def main():
    cs = SmartClamp(1)
    cs.updateSerialPorts()
    cs.checkConnect()

if __name__ == '__main__':
    main()
