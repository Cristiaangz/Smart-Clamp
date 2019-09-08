#
#   FILE: smartclamp
#   AUTHOR: Cristian Garcia (Based on turbidostat.py by Christian Wohltat, Stefan Hoffman)
#   DATE: 2019 17 03
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
import re
import os
import configparser
import datetime
import string
from pylab import *
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
import logging

mpl_logger = logging.getLogger("matplotlib")
mpl_logger.setLevel(logging.WARNING)                                            # Supresses matplotlib debug messages when liveplotting

SCVERSION = 0.13
BAUD_RATE = 115200

print("\n\nSTART")
print("SMARTCLAMP.PY VERSION: ",SCVERSION)

CMDlist = [
"Connect: connect to Smart Clamp",
"Disconnect: disconnect from Smart Clamp",
"Test: Automatic Tests",
"LON: Turn on Laser / LED",
"LOF: Turn off Laser / LED",
"MON: Turn on MPU",
"MOF: Turn off MPU",
"SON: Turn on Light Sensor",
"SOF: Turn off Light Sensor",
"Sample: Set Sampling Rate",
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

sc = []

##################################################
##
##  Classes
##
##########################

class SmartClamp:
    def __init__(self, ID, logname, lightIntensity):
        self.ID = ID
        self.data_source =  None                                                ## Serial Address where data is being read from
        self.connected = False
        self.connecting = False
        self.done = False
        self.ser = None                                                         ## Stores the serial connection
        self.lock = threading.Lock()                                            ## Threading Lock


        #Variables for logging
        self.logFileName = logname                                              ## Name of logfile

        #Variables for Tests
        self.testDone = threading.Event()                                       ## Event to signal test is done
        self.testContinue = threading.Event()                                   ## Event to signal test may continue to next stage
        self.targetTime = -1                                                    ## Target time for next the testContinue flag to be set

        #Variables for Arduino
        self.second = 0                                                         ## Second since SmartClamp started collecting data
        self.msecs = -1                                                         ## Millisecond of latest retrieved data
        self.verbose = False                                                    ## DEBUG: Prints the readings to terminal

        #Variables for Light Sensor
        self.Ia = 0                                                             ## Intensity of Light to Frequency sensor in uW/m2

        #Variables for Light Source
        self.LightOn = False
        self.lightInt = lightIntensity                                          ## Byte value to control voltage delivered to LED through digital Potentiometer

        #Variables for Gyro
        self.calibrated = threading.Event()                                     ## Event to indicate if gyroscope is calibrated

        self.acc_x = 0
        self.acc_y = 0
        self.acc_z = 0
        self.temp_mpu = 0
        self.gyro_x = 0
        self.gyro_y = 0
        self.gyro_z = 0
        self.gyro_x_cal = 0                                                     # Offset according to Gyro's starting position
        self.gyro_y_cal = 0
        self.gyro_z_cal = 0

        #Variables for plotting
        self.times = []
        self.Ias = []
        self.LONs = []
        self.acc_xs = []
        self.acc_ys = []
        self.acc_zs = []
        self.temp_mpus = []
        self.gyro_xs = []
        self.gyro_ys = []
        self.gyro_zs = []



    def __delete__(self):                                                       ## Delete protocol (Untested)
        self.closeSerialSession()


    def findSerialPorts(self):                                                  ## Looks for USB serial devices connected.
                                                                                ##      NOTE: Assumes only a single device is connected through USB
        if self.verbose:
            print("Updating Serial Ports")

        self.serialport_list = serial.tools.list_ports.comports()               ## Retrieves list of all connected Serial Ports

        if os.name == 'posix':                                                  ## If running on MacOS
            if self.verbose:
                print ("\tmacOS detected")
            self.serialports = [ row[0] for row in self.serialport_list if 'usb' in row[0]]
            if len(self.serialports) > 0:
                self.m_tcPort = self.serialports[0]
                if self.verbose:
                    print("\tFound USB serial port: ",self.m_tcPort)
        elif os.name == 'nt':                                                   ## If running on Windows
            if self.verbose:
                print ("\tWindows detected")
            self.serialports = [ row[0] for row in serialport_list if 'COM' in row[0]]
            if len(self.serialports) > 0:
                self.m_tcPort = self.serialports[0]
                if self.verbose:
                    print("\tFound USB serial port: ",self.m_tcPort)

    def checkConnect(self):                                                     ## Checks if Smartclamp is connected, and starts serial connection if that's the case.
        if self.verbose:
            print("\nChecking Connection")
        if not self.connected and not self.connecting:
            if self.verbose:
                print("\tNot connected")
            try:
                self.data_source = self.m_tcPort
                self.startSerialSession()
            except AttributeError:
                print("\tNo valid USB connections were found")
            except OSError:
                print(self.data_source, " is already connected to another program")
            except:
                print("Something went wrong when starting the Serial Session")
        if self.ser:
            print ("\nThreads Starting\n")
            self.serialThread.start()

        else:
            print ("\nConnection unsuccessful\n")


    def startSerialSession(self):                                               ## OPTIMIZE: Should merge this function with connect()
        if self.verbose:
            print("\tStarting Serial Session")
        self.connect( self.data_source )
        self.connecting = False

    def connect(self, data_source):
        if self.verbose:
            print("\tTrying to connect to ", data_source)

        # now connect with correct speed
        self.ser = serial.Serial(data_source, BAUD_RATE, timeout=0)
        self.ser.flush()

        if self.ser:
            print("\nConnected to ", data_source)
            self.connected = True
            self.connecting = False
            self.done = False

            # self.logFilePath = logFileFolder + self.logFileName + '.txt'

            self.logFilePath_csv = logFileFolder + self.logFileName + '.csv'
            # self.logfile = open(self.logFilePath, 'w+')                 # Change to w+ to constantly overwrite
            self.logfile_csv = open(self.logFilePath_csv, 'a+')
            self.serialThread = threading.Thread(target=self.SerialThread, name='Serial Stream')
            self.serialThread.setDaemon(True)

    def closeSerialSession(self):
        self.ser.write('LOF\n'.encode())
        self.done = True
        self.serialThread.join()
        self.disconnect()
        print("Disconnected from Smart Clamp {} at {}".format(self.ID, self.data_source))

    def disconnect(self):
        # if self.logfile:
        #     self.logfile.close()
        self.logfile_csv.close()
        self.connecting = False
        self.connected = False
        if self.ser:
            self.ser.close()
            self.ser = None

        ### Writing Logs

    def SerialThread(self):
        self.lock.acquire()

        self.xs = []
        self.ys = []

        temp_response = ""
        response = ""

        new_sample_available = False
        self.new_sample_available = False

        self.LogToCSVFile('Time [s],Intensity A,Laser On,AcX,AcY,AcZ,GyX,GyY,GyZ,MPU Temp [C]\n')
        #self.LogToTxtFile('Time [s]\tIntensity A\tLaser On\tAcX\tAcY\tAcZ\tGyX\tGyY\tGyZ\tMPU Temp [C]\n')

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
                except:
                    print ('except when reading response')
                    self.connected = False
                    self.connecting = True
                    continue

                if len(response) > 1 and response[-3] == '$':
                    response = response[:-3] + response[-2:-1]
                    # print(response)
                    #print(response[-3])

                    if response.find('START') == 0:
                        ## Procedures to do at Start. May be replicated for other comms
                        print("\nCALIBRATING. Dont Move The Smart Clamp")
                        pass
                    if response.find('READY') == 0:
                        ## Procedures to do at Start. May be replicated for other comms
                        print("\nCalibration Done")
                        self.calibrated.set()
                        if self.verbose:
                            print('\nStart Time:', datetime.datetime.now().strftime('%H:%M:%S'), "\n")
                            print('Time [s]\tIntensity\tLight\tAx\tAy\tAz\tGx\tGy\tGz\tMPU Temp [C]\n')
                        pass

                    for (var, value) in re.findall(r'([^=\t ]*)=([-0-9\.]+)', response):
                        # find 0 or more (*) strings that start (^) with a tab (\t) and are
                        # followed by one or more (+) numbers from 0-9 ignoring \.



                        if var == 't':
                            if value != self.second:
                                # self.new_sample_available = True
                                self.second = int(value)
                                if self.second == self.targetTime:
                                    self.testContinue.set()

                        if var == 'ms':
                            self.new_sample_available = True
                            self.msecs = int(value)

                        elif var == 'I':
                            self.Ia = float(value)/6

                        elif var == 'l':
                            self.LightOn = bool(value)

                        # Check if gyro values

                        elif var == 'ax':
                            self.acc_x = float(value)/4096

                        elif var == 'ay':
                            self.acc_y = float(value)/4096

                        elif var == 'az':
                            self.acc_z = float(value)/4096

                        elif var == 'gx':
                            self.gyro_x = float(value)/65.5
                            self.new_sample_available = True

                        elif var == 'gy':
                            self.gyro_y = float(value)/65.5

                        elif var == 'gz':
                            self.gyro_z = float(value)/65.5

                        elif var == 'tm':
                            self.temp_mpu = (float(value)+ 12412.0)/340.0

                        elif var == 'gxc':
                            self.gyro_x_cal = float(value)

                        elif var == 'gyc':
                            self.gyro_y_cal = float(value)

                        elif var == 'gzc':
                            self.gyro_z_cal = float(value)

                    response = ""


                if self.new_sample_available:

                #Update data list

                    if self.msecs < 100:
                        self.times.append(float('{}.0{}'.format(self.second, self.msecs)))
                    else:
                        self.times.append(float('{}.{}'.format(self.second, self.msecs)))
                    self.Ias.append(self.Ia)
                    self.LONs.append(self.LightOn)
                    self.acc_xs.append(self.acc_x)
                    self.acc_ys.append(self.acc_y)
                    self.acc_zs.append(self.acc_z)
                    self.temp_mpus.append(self.temp_mpu)
                    self.gyro_xs.append(self.gyro_x)
                    self.gyro_ys.append(self.gyro_y)
                    self.gyro_zs.append(self.gyro_z)

                    if self.msecs < 100:
                        logstring = '{}.0{},{},{},{},{},{},{},{},{},{}\n'.format(self.second, self.msecs, self.Ia, self.LightOn, self.acc_x, self.acc_y, self.acc_z, self.gyro_x, self.gyro_y, self.gyro_z, self.temp_mpu)
                    else:
                        logstring = '{}.{},{},{},{},{},{},{},{},{},{}\n'.format(self.second, self.msecs, self.Ia, self.LightOn, self.acc_x, self.acc_y, self.acc_z, self.gyro_x, self.gyro_y, self.gyro_z, self.temp_mpu)

                    if self.verbose:
                        print (datetime.datetime.now().strftime('%H:%M:%S'), logstring, sep=" | ")


                    self.LogToCSVFile(logstring)

                    # self.lock.acquire()
                    # # if not self.logfile:
                    # self.logfile = open(self.logFilePath, 'w+')                 # Change to w+ to constantly overwrite
                    # self.LogToTxtFile(logstring)
                    # self.logfile.close()
                    # self.lock.release()
                    self.new_sample_available = False



    def LogToFile(self, f, s):
        f.write(s)

        try:
            f.flush()
        # ignore and flush later ('magically' locked file, e.g. by excel import)
        except IOError:
            if e.errno != 13:
                debug_log.write(str(e.errno) + '\n')

    # def LogToTxtFile(self, s):
    #     self.LogToFile( self.logfile, s)

    def LogToCSVFile(self, s):
        self.LogToFile( self.logfile_csv, s)

    def plotThread(self):
        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(1,1,1)

        self.livePlot = animation.FuncAnimation(self.fig, self.animate, interval=1000)

        #Live Plot Labels
        plt.xlabel("Time [s]")
        plt.ylabel("Irradience [W/m^2]")
        plt.title("Light Sensor Live Plot")
        plt.legend()

        plt.show()

    def animate(self, label):
        self.ax1.clear()
        self.ax1.plot(self.times, self.Ias, label="irradience")
        if self.done:
            plt.savefig(logFileFolder + self.logFileName + '.png')
            self.livePlot.event_source.stop()
            print("\n\nGraph Saved. Close the graph to start next test.")

    def brightTest(self, timeInt=20, numLevels = 8):
        level = 1
        if self.connected and self.LightOn:
            self.ser.write('LOF\n'.encode())
            self.LightOn = False
        self.calibrated.wait()
        while self.connected:
            if self.second > ((level * timeInt) - 1):
                print("self.second: ", self.second)
                level += 1
                if level == 2:
                    self.ser.write('LON\n'.encode())
                    print('Light Turned On')
                if level > 2 and level <= numLevels:
                    self.lightInt -= 1

                cmd = "SLI "+ str(self.lightInt)+"\n"
                self.ser.write(cmd.encode())
                print("Potentiometer Level: ", self.lightInt)

            if level > numLevels and self.second > (numLevels * timeInt) :
                self.ser.write('LOF\n'.encode())
                self.LightOn = False
                self.done = True
                self.testDone.set()
                break

    def samplingTest(self, timeInt=60, intensity=105, light_Sampling=100, mpu_Sampling = 100):
        print("Sampling Test Started")
        self.calibrated.wait()

        # Set appropriate intensity
        cmd = "SLI "+ str(intensity)+"\n"
        self.ser.write(cmd.encode())

        #Set light sampling rate
        self.ser.write('SON\n'.encode())
        cmd = "SLS "+ str(light_Sampling)+"\n"
        self.ser.write(cmd.encode())

        #Set MPU Sampling Rate
        self.ser.write('MOF\n'.encode())
        cmd = "SMS "+ str(mpu_Sampling)+"\n"
        self.ser.write(cmd.encode())

        # Start with only Light sensor on
        self.ser.write('LON\n'.encode())
        self.LightOn = True

        self.targetTime = (timeInt)
        self.testContinue.wait()
        self.testContinue.clear()

        print("MPU Mode")
        self.ser.write('SOF\n'.encode())
        self.ser.write('MON\n'.encode())
        self.light_Mode = False
        self.targetTime = (timeInt*2)
        self.testContinue.wait()
        self.testContinue.clear()
        self.testDone.set()
        self.done = True


##################################################
##
##  Main Loop Functions
##
##########################

def processInput(input, ID=0):
    #print("The Input was :", input)
    # print("ID is: ", ID)
    switcher={
        'CONNECT': connectToSC ,
        'DISCONNECT': disconnectFromSC,
        'D' : disconnectFromSC,
        'QUIT': quitProg,
        'Q': quitProg,
        'LON' : LON,
        'LOF' : LOF,
        'MON' : MON,
        'MOF' : MOF,
        'SON' : SON,
        'SOF' : SOF,
        'V' : verbose,
        'SLI' : setLightIntensity,
        'PLOT' : plot,
        'P' : plot,
        'TEST' : test,
        'CHECK' : checkSC,
        'SAMPLE' : setSampling
    }
    func=switcher.get(input, invalidCmd)
    try:
        return func(ID)
    except TypeError:
        print("There was a TypeError when running", func)
        return
    except IndexError:
        print("Not connected to a Smartclamp")

def checkSC(ID):
    print("Current default ID: ")
    print ("Smartclamp objects: ", sc)


def connectToSC(ID, logname=datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), lightIntensity = 128):
    sc.append(SmartClamp(ID, logname, lightIntensity))
    print("Created Smart Clamp ID: ", sc[ID].ID)
    sc[ID].findSerialPorts()
    sc[ID].checkConnect()

def test(ID):
    while True:
        try:
            test = int(input("Please choose a test:\n\n1) Bright Test\n2) Sampling Test\n>>\t"))
            switcher={
                1 : brightnessTest,
                2 : samplingTest
            }
            func=switcher.get(test, invalidCmd)
            try:
                return func(ID)
            except TypeError:
                print("There was a TypeError when running", func)
                return
        except TypeError:
            print("Incorrect Input")

def samplingTest(ID):
    if (len(sc) == 0) or not sc[ID].connected:
        connectToSC(ID)

    testThread = threading.Thread(target=sc[ID].samplingTest, name='Sampling Test')
    testThread.setDaemon(True)
    if sc[ID].connected:
        testThread.start()
        sc[ID].plotThread()
        sc[ID].testDone.wait()
        sc[ID].testDone.clear()
    disconnectFromSC(ID)

def brightnessTest(ID):
    try:
        timeInt = int(input("Set Time Interval Between Levels [seconds]: "))
        numLevels = int(input("Set Number of Levels Testes [Min 2]: "))
        initLightIntensity = int(input("Set Initial Light Intensity [32-128]: "))
        runs = int(input("Set Number of Runs: "))
        livePlot = input("Show Live Plot? (Y/N): ").upper()
        naming = input("Custom Test Name? (Y/N): ").upper()
        if naming == 'Y':
            logname = input("Enter Log Name [no spaces]: ")

        for run in range(runs):
            print("-------------------------------------------------------------------")
            print("\nStarting Brightness Test ", run+1)
            if (len(sc) == 0) or not sc[ID].connected:
                if naming == 'Y':
                    connectToSC(ID, logname + "_" + str(run+1), initLightIntensity)
                else:
                    connectToSC(ID, lightIntensity=initLightIntensity)

            testThread = threading.Thread(target=sc[ID].brightTest, args=(timeInt, numLevels), name='Brightness Test')
            testThread.setDaemon(True)
            if sc[ID].connected:
                testThread.start()
                if livePlot == "Y":
                    sc[ID].plotThread()
                sc[ID].testDone.wait()
            disconnectFromSC(ID)
            print("Finished test ", run+1)
    except:
        print("Something went wrong with Brightness Test")


def disconnectFromSC(ID):
    sc[ID].closeSerialSession()
    del sc[ID]

def quitProg(ID):
    for device in sc:
        if sc[ID].ser:
            sc[ID].closeSerialSession()
    sys.exit()

def LON(ID):
    try:
        sc[ID].ser.write('LON\n'.encode())
    except AttributeError:
        print("Not connected to Smart Clamp (>> connect)")

def LOF(ID):
    try:
        sc[ID].ser.write('LOF\n'.encode())
    except AttributeError:
        print("Not connected to Smart Clamp (>> connect)")

def MON(ID):
    try:
        sc[ID].ser.write('MON\n'.encode())
    except AttributeError:
        print("Not connected to Smart Clamp (>> connect)")

def MOF(ID):
    try:
        sc[ID].ser.write('MOF\n'.encode())
    except AttributeError:
        print("Not connected to Smart Clamp (>> connect)")

def SON(ID):
    try:
        sc[ID].ser.write('SON\n'.encode())
    except AttributeError:
        print("Not connected to Smart Clamp (>> connect)")

def SOF(ID):
    try:
        sc[ID].ser.write('SOF\n'.encode())
    except AttributeError:
        print("Not connected to Smart Clamp (>> connect)")

def verbose(ID):
    try:
        sc[ID].verbose = not(sc[ID].verbose)
        print("verbose is", sc[ID].verbose)
    except AttributeError:
        print("Not connected to Smart Clamp (>> connect)")

def setLightIntensity(ID):
    while True:
        try:
            intensity = int(input("Set intensity to [0-128]: "))
        except ValueError:
            print("Please enter an integer from 0 to 128")
            continue
        try:
            if (0 <= intensity <= 128):
                cmd = "SLI "+ str(intensity)+"\n"
                sc[ID].ser.write(cmd.encode())
                sc[ID].potentiometer = cmd
                break
        except AttributeError:
            print("Not connected to Smart Clamp (>> connect)")
            break

def setSampling(ID):
    while True:
        try:
            device = int(input("Set Sampling for:\n\t1)Light Detector\n\t2)MPU\n>>\t"))
            sampling = int(input("Set sampling to [1-100]: "))
        except ValueError:
            print("Please enter an integer from 0 to 100")
            continue
        try:
            if (1 <= sampling <= 100):
                if device == 1:
                    cmd = "SLS "+ str(sampling)+"\n"
                    sc[ID].ser.write(cmd.encode())
                    break
                if device == 2:
                    cmd = "SMS "+ str(sampling)+"\n"
                    sc[ID].ser.write(cmd.encode())
                    sc[ID].potentiometer = cmd
                    break
                else:
                    print("Invalid device Number")
                    break
        except AttributeError:
            print("Not connected to Smart Clamp (>> connect)")
            break

def plot(ID):
    sc[ID].plotThread()

def invalidCmd(ID):
    print("Invalid command\n")

exit = False

##################################################
##
##  Main Loop
##
##########################

def main():
    while not exit:
        inp = input("\n>> ")
        if len(sc) > 1:
            print("List of SmartClamp IDs")
            for smartclamp in sc:
                print(smartclamp.ID)
            ID = int(input("Enter Smart Clamp ID: "))
            processInput(inp.upper(), ID)
        else:
            processInput(inp.upper())

if __name__ == '__main__':
    main()
