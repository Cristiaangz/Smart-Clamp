#!/usr/bin/python
# pylint: disable-msg=C0103, W0311, C0301, W0401

import wx
import thread
import serial
import serial.tools.list_ports
import sys
from time import sleep
import re
import os
import ConfigParser
import datetime
import string
from pylab import *
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from scipy.stats import linregress

import wxturbidostat


homeFolder = os.path.expanduser("~")
logFileFolder = homeFolder + '/Turbidostat/logs/'
if not os.path.exists(logFileFolder):
    os.makedirs(logFileFolder)
sys.stderr = open(logFileFolder + 'stderr.log', 'w')
debug_log = open(logFileFolder + 'debug.log', 'w+')

def jaccsd(fun, x_in):
    '''Jacobian through complex step differentiation'''
    x_out = fun(x_in)
    n = x_in.size
    m = x_out.size
    A = matrix(zeros([m,n]))
    eps = ((1+2e-16) - 1)
    h = n*eps
    for k in range(n):
        x1 = matrix(x_in, dtype=complex)
        x1[k,0]  = x1[k, 0] + h*1j;
        A[:,k] = imag(fun(x1))/h
    return (x_out, A)



def ekf(fstate, x, P, hmeas, z, Q, R, I0=None):
    # (x1,A) = jaccsd(fstate,x);    #nonlinear update and linearization at current state
    x1 = fstate(x)
    A = matrix(r_[[[float(x[1]), float(x[0])], [0.0, 1.0]]])


    A = matrix(A)
    P = matrix(P)

    P = A*P*A.T + Q              # partial update
    # z1, H = jaccsd(hmeas, x1)    # nonlinear measurement and linearization
    z1 = hmeas(x1)
    H = matrix( r_[-(I0*log(10))/10**float(x1[0]) , 0 ] )

    P12 = P*H.T                  # cross covariance


    K = P12*inv(H*P12+R)         # Kalman filter gain
    x = x1+K*(z-z1)              # state estimate
    P = P-K*(P12.T)              # state covariance matrix

    return x, P, K


class TurbidostatGUI(wxturbidostat.TsFrame):
    def __init__(self, parent):

        #self.m_notebook.InvalidateBestSize()
        # import ipdb; ipdb.set_trace()

        wxturbidostat.TsFrame.__init__( self, parent )

        self.Show(True)

        self.threads = 0
        self.thread_lock = thread.allocate_lock()
        self.connected = False
        self.connecting = False
        self.ser = None
        self.done = False

        self.m_widgetGroup = (self.m_txtODText, self.m_txtOD, self.m_btnSetI0,\
                              self.m_txtOD1cmText, self.m_txtOD1cm,\
                              self.m_txtTargetODText, self.m_tcTargetOD, self.m_btnSetTargetOD,\
                              self.m_rbPumpMode, self.m_txtManualPump, self.m_tbManualPump,\
                              self.m_txtPumpInterval, self.m_tcPumpInterval, self.m_txtPumpIntervalUnit, self.m_btnSetPumpInterval,\
                              self.m_txtPumpDuration, self.m_tcPumpDuration, self.m_txtPumpDurationUnit, self.m_btnSetPumpDuration,\
                              self.m_txtPumpPower, self.m_sldPumpPower, self.m_txtPumpPowerPercentage, self.m_btnSetPumpPower,\
                              self.m_txtAirpumpPower, self.m_sldAirpumpPower, self.m_txtAirpumpPowerPercentage, self.m_btnSetAirpumpPower,\
                              self.m_txtStirrerSpeedText, self.m_txtStirrerSpeed, self.m_txtStirrerSpeedUnit,\
                              self.m_txtStirrerTargetSpeed, self.m_tcStirrerTargetSpeed, self.m_txtStirrerTargetSpeedUnit, self.m_btnSetStirrerTargetSpeed)
        self.m_widgetGroupAutomaticPump = (self.m_txtPumpInterval, self.m_tcPumpInterval, self.m_txtPumpIntervalUnit, self.m_btnSetPumpInterval,\
                                  self.m_txtPumpDuration, self.m_tcPumpDuration, self.m_txtPumpDurationUnit, self.m_btnSetPumpDuration)
        self.m_widgetGroupManualPump = (self.m_txtManualPump, self.m_tbManualPump)

        for widget in self.m_widgetGroup:
            widget.Disable()


        # find serial ports
        self.data_source =  None
        serialport_list = serial.tools.list_ports.comports()
        if os.name == 'posix':
            serialports = [ row[0] for row in serialport_list if 'USB' in row[0]]
            if len(serialports) > 0:
                self.m_tcPort.SetValue(serialports[0])
        elif os.name == 'nt':
            serialports = [ row[0] for row in serialport_list if 'COM' in row[0]]
            if len(serialports) > 0:
                self.m_tcPort.SetValue(serialports[0])

        # # check for product string
        # import usb
        # busses = usb.busses()
        # bus = busses.next()
        # for k in range(4): print usb.util.get_string(bus.devices[1].dev, k, 0)


        # Set Icons
        icons = wx.IconBundle()
        favicon = wx.Icon('./res/turbidostat.ico', wx.BITMAP_TYPE_ICO, 16, 16)
        icons.AddIcon(favicon)
        favicon = wx.Icon('./res/turbidostat.ico', wx.BITMAP_TYPE_ICO, 32, 32)
        icons.AddIcon(favicon)
        self.SetIcons(icons)

        # load configuration from config file
        configParser = ConfigParser.RawConfigParser()
        configFilePath = homeFolder + '/Turbidostat/turbidostat.cfg'
        configParser.read(configFilePath)
        self.OD1cm_factor = configParser.getfloat('MEASUREMENT', 'OD_1cm_factor')
        # configParser.set('MEASUREMENT', 'OD_1cm_factor', self.OD1cm_factor*2) # save some configuration
        with open(configFilePath, 'wb') as configfile:
            configParser.write(configfile)
        self.logfile = None
        self.logfile_csv = None

        self.starttime = 0.0
        self.I0 = nan
        self.I = nan
        self.stirrer_speed = nan
        self.pump = False
        self.dummy_mode = False

        # ---- Kalman ----
        # Zustandsmodell exponentielles Wachstum
        self.f = lambda(x): matrix( [x[0, 0]*x[1, 0], x[1, 0]] )

        # Measurement
        self.h = lambda(x): matrix( self.I0/(10**x[0,0]) )

        self.OnKalmanReset(None)

        # PLOT
        fig = figure()
        # fig.patch.set_facecolor( (214/255, 214/255, 214/255))
        fig.patch.set_facecolor( array(self.m_pnlGraphs.GetBackgroundColour()[0:3])/255.0)

        self.canvas = FigureCanvas(self.m_pnlGraphs, -1, fig)
        self.toolbar = NavigationToolbar2Wx(self.canvas)
        self.toolbar.Realize()
        self.toolbar.SetSize(wx.Size(-1, 10))
        self.toolbar.DeleteToolByPos(1)
        self.toolbar.DeleteToolByPos(1)
        self.toolbar.DeleteToolByPos(5)
        self.toolbar.DeleteToolByPos(1)
        self.toolbar.DeleteToolByPos(1)
        self.toolbar.DeleteToolByPos(1)
        self.toolbar.DeleteToolByPos(0)
        self.toolbar.DeleteToolByPos(0)

        # add
        resettool = self.toolbar.AddLabelTool(id = wx.ID_ANY, label='reset', bitmap=wx.Bitmap('./res/reset.png'))
        self.toolbar.Realize()
        self.Bind(wx.EVT_TOOL, self.OnKalmanReset, resettool)

        self.toolbar.SetBackgroundColour( array(self.m_pnlGraphs.GetBackgroundColour()[0:3]) )

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.toolbar, 0, wx.LEFT | wx.TOP )
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.m_pnlGraphs.SetSizer(self.sizer)
        self.m_pnlGraphs.Fit()

        subplot(211)
        self.ax = []
        self.ax.append( plot(r_[1:2], 'b', r_[4:5], 'r--', r_[4:5], 'r--', r_[4:5], 'g-', r_[4:5], 'r--', r_[4:5], 'r--')  )
        subplot(212)
        hold(True)
        self.ax.append( plot(r_[1:2], 'c', r_[2:3], 'b', r_[4:5], 'r--', r_[4:5], 'r--') )
        # show()

    def connect(self, data_source):
        try:
            # workaround for reconnect bug in linux
            self.ser = serial.Serial(data_source, 9600, timeout=0)
            self.dummy_mode = False
        except:
            self.ser = None
            try:
                # open prerecorded file
                self.dummy_file = open(data_source)
                self.dummy_mode = True
            except:
                self.dummy_mode = False

        # connect to serial device
        if self.ser:
            # first close lower speed serial connection (linux workaround)
            self.ser.close()

            # now connect with correct speed
            self.ser = serial.Serial(data_source, 115200, timeout=0)
            self.ser.flush()

        if self.ser or self.dummy_mode:
            self.connected = True
            self.connecting = False
            self.done = False

            logFilePath = logFileFolder + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.txt'
            self.logfile = open(logFilePath, 'w+')

            logFilePath_csv = logFileFolder + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.csv'
            self.logfile_csv = open(logFilePath_csv, 'w+')
            thread.start_new_thread(self.SerialThread, ())


    def disconnect(self):
        self.I0 = nan
        self.logfile.close()
        self.connected = False
        if self.ser:
            self.ser.close()
            self.ser = None

    def openSerialSession(self):
        self.connect( self.data_source )
        self.LogToCSVFile('#time [s]\tIntensity\tOD measured\tOD estimate\tOD estimate uncertainty\tdoubling rate [db/hr]\tdoubling rate uncertainty [db/hr]\tstirrer speed [rpm]\ttemperature [degree C])\n')

        self.pump = False
        self.n_pump_distrust = 10
        self.invalid_samples_left = self.n_pump_distrust
        self.connecting = False



    def closeSerialSession(self):
        self.done = True
        sleep(0.2)
        self.connecting = False
        self.disconnect()

    def OnConnect(self, event):
        if not self.connected and not self.connecting:
            self.data_source = self.m_tcPort.GetValue()
            self.openSerialSession()

            if self.ser:
                for widget in self.m_widgetGroup:
                    widget.Enable()
                self.OnSelectPumpMode(event) # disable unselected pump mode widgets
                print 'connection successful\n'

            # stop if no valid data source available
            if self.ser == None and self.dummy_mode == False:
                dlg = wx.MessageDialog(self, "Cannot connect to turbidostat" + self.data_source, "Warning", wx.OK)
                dlg.ShowModal()
                dlg.Destroy()

            if self.ser or self.dummy_mode:
                self.m_btnConnect.SetLabel('disconnect')
                self.m_bitmConnected.SetBitmap(wx.Bitmap( './res/connected.png'))
                self.m_tcPort.Disable()

        else:
            self.closeSerialSession()
            self.m_btnConnect.SetLabel('connect')
            self.m_bitmConnected.SetBitmap(wx.Bitmap('./res/disconnected.png'))
            self.m_tcPort.Enable()
            for widget in self.m_widgetGroup:
                widget.Disable()
            print 'disconnection successful\n'

    def setTime( self, time ):
        cmd = 'ST ' + str(int(time)) + chr(10)
        print cmd
        self.ser.write(cmd.encode())

    def OnSetI0( self, event ):
        cmd = 'SI0 ' + chr(10)
        print cmd
        self.ser.write(cmd.encode())

    def OnSetTargetOD( self, event ):
        od = self.m_tcTargetOD.GetValue()
        cmd = 'SOD ' + od + chr(10)
        print cmd
        self.ser.write(cmd.encode())

    def OnSetPumpInterval(self, event):
        duration = self.m_tcPumpInterval.GetValue()
        cmd = 'SPW ' + duration + chr(10)
        print cmd
        self.ser.write(cmd.encode())

    def OnSetPumpDuration(self, event):
        duration = self.m_tcPumpDuration.GetValue()
        cmd = 'SPD ' + duration + chr(10)
        print cmd
        self.ser.write(cmd.encode())

    def OnPumpPowerSlider(self, event):
        power = self.m_sldPumpPower.GetValue()
        self.m_txtPumpPowerPercentage.SetLabel('%.1f'%(100.0*power/255)+'%')

    def OnAirpumpPowerSlider(self, event):
        power = self.m_sldAirpumpPower.GetValue()
        self.m_txtAirpumpPowerPercentage.SetLabel('%.1f'%(100.0*power/255)+'%')

    def OnSetPumpPower(self, event):
        power = self.m_sldPumpPower.GetValue()
        print power
        cmd = 'SPP ' + str(power) + chr(10)
        print cmd
        self.ser.write(cmd.encode())

    def OnSetAirpumpPower(self, event):
        power = self.m_sldAirpumpPower.GetValue()
        print power
        cmd = 'SAP ' + str(power) + chr(10)
        print cmd
        self.ser.write(cmd.encode())

    def OnSetStirrerTargetSpeed(self, event):
        rpm = self.m_tcStirrerTargetSpeed.GetValue()
        cmd = 'SSS ' + rpm + chr(10)
        print cmd
        self.ser.write(cmd.encode())

    def OnSelectPumpMode(self, event):
        if self.m_rbPumpMode.GetSelection() == 0: # automatic
            self.m_tbManualPump.SetValue(False)
            self.OnManualPump(event)
            for widget in self.m_widgetGroupAutomaticPump:
                widget.Enable()
            for widget in self.m_widgetGroupManualPump:
                widget.Disable()
            cmd = 'SPM ' + '0' + chr(10)
        else:
            for widget in self.m_widgetGroupAutomaticPump:
                widget.Disable()
            for widget in self.m_widgetGroupManualPump:
                widget.Enable()
            cmd = 'SPM ' + '1' + chr(10)
        print cmd
        self.ser.write(cmd.encode())

    def OnManualPump(self, event):
        if self.m_tbManualPump.GetValue():
            self.m_tbManualPump.SetLabel('on')
            cmd = 'SMP ' + '1' + chr(10)
        else:
            self.m_tbManualPump.SetLabel('off')
            cmd = 'SMP ' + '0' + chr(10)

        print cmd
        self.ser.write(cmd.encode())

    def OnClose(self, event):
        self.done = True
        print 'done: ' + str(self.done)
        # dlg = wx.MessageDialog(self,
        #     "Do you really want to close this application?",
        #     "Confirm Exit", wx.OK|wx.CANCEL|wx.ICON_QUESTION)
        # result = dlg.ShowModal()
        # dlg.Destroy()
        # if result == wx.ID_OK:
        self.Destroy()


    def LogToFile(self, f, s):
        f.write(s)

        try:
            f.flush()
        # ignore and flush later ('magically' locked file, e.g. by excel import)
        except IOError, e:
            if e.errno != 13:
                debug_log.write(str(e.errno) + '\n')

    def LogToTxtFile(self, s):
        self.LogToFile( self.logfile, s)

    def LogToCSVFile(self, s):
        self.LogToFile( self.logfile_csv, s)


    def OnKalmanReset(self, event):
        # covariance of process
        self.Q = matrix([[0, 0],
                         [0, 5*10**(-13)]])

        # covariance of measurement
        self.R = 40**2
        self.P_OD = self.R/((self.I0*log(10))**2)



        # Initialisierung
        self.I = nan
        self.x = matrix( [log10(self.I0/self.I0), 1.0000 ]).T          # initial state
        self.P = matrix( [[self.P_OD,           0],
                          [0,         (0.0005)**2]] )                   # initial state covariance

        self.thread_lock.acquire()
        self.invalid_samples_left = 0

        # self.time_list               = self.time_list[-1]
        # self.measurement_list        = self.measurement_list[-1]
        # self.state_list              = self.state_list[-1]
        # self.dbrate_list             = self.dbrate_list[-1]
        # self.dbrate_uncertainty_list = self.dbrate_uncertainty_list[-1]
        # self.uncertainty_list        = self.uncertainty_list[-1]
        self.time_list               = []
        self.measurement_list        = []
        self.state_list              = []
        self.dbrate_list             = []
        self.dbrate_uncertainty_list = []
        self.uncertainty_list        = []

        self.thread_lock.release()

    def plot(self):
        if self.dummy_mode == False or (self.dummy_mode and (self.time % 0.5 == 0)):
            self.thread_lock.acquire()
            subplot(211)
            self.ax[0][0].set_xdata( self.time_list )
            self.ax[0][0].set_ydata( self.dbrate_list)
            self.ax[0][1].set_xdata( self.time_list)
            self.ax[0][1].set_ydata( r_[self.dbrate_list] - r_[self.dbrate_uncertainty_list])
            self.ax[0][2].set_xdata( self.time_list)
            self.ax[0][2].set_ydata( r_[self.dbrate_list] + r_[self.dbrate_uncertainty_list])
            xlim( 0, self.time_list[-1])
            # ylim( min(r_[self.dbrate_list] - r_[self.dbrate_uncertainty_list]),
            #                    max(r_[self.dbrate_list] + r_[self.dbrate_uncertainty_list]))
            ylim( min(r_[self.dbrate_list]), max(r_[self.dbrate_list] + r_[self.dbrate_uncertainty_list]))
            ylabel( 'rate [doublings/hr]')

            subplot(212)
            self.ax[1][0].set_xdata( self.time_list )
            self.ax[1][0].set_ydata( self.measurement_list )
            self.ax[1][1].set_xdata( self.time_list )
            self.ax[1][1].set_ydata( self.state_list )
            self.ax[1][2].set_xdata( self.time_list )
            self.ax[1][2].set_ydata( r_[self.state_list] - sqrt(r_[self.uncertainty_list]) )
            self.ax[1][3].set_xdata( self.time_list )
            self.ax[1][3].set_ydata( r_[self.state_list] + sqrt(r_[self.uncertainty_list]) )
            xlim( 0, self.time_list[-1] )
            ylim( min(self.measurement_list), max(r_[self.measurement_list]+ sqrt(r_[self.uncertainty_list])))
            xlabel('time [min]')
            ylabel('OD')
            self.canvas.draw()
            # self.Fit)
            self.thread_lock.release()

            if (self.OD < -110):
                self.OD = 'n/A(-)'
                OD_1cm = 'n/A(-)'
            else:
                OD_1cm = self.OD*self.OD1cm_factor
            self.m_txtOD.SetLabel( str(round(self.OD, 3)))
            self.m_txtOD1cm.SetLabel( str(round(OD_1cm, 3)))

    def SerialThread(self):
        if self.threads > 0:
            return

        self.threads += 1
        # print 'nthreads ', self.threads
        new_sample_available = False


        response = ''
        while not self.done:
            if self.connected:
                if self.dummy_mode:
                    response = self.dummy_file.readline()
                else:
                    try:
                        response = response + self.ser.readline()
                    except :
                        print 'except'
                        self.connected = False
                        self.connecting = True
                        continue

                if len(response) > 1 and response[-1] == '\n':
                    if response.find('START') == 0 and len(self.time_list) > 0:
                        # self.time = self.time + 2.0/60
                        self.setTime(self.time*60*1000)

                    if response.find('I_0') == 0:
                        self.I0 = float(response[4:])
                        self.P[0, 0] = self.P_OD
                        self.x[0, 0] = log10(self.I0/self.I)

                    if response.find('Pump On') > -1:
                        self.pump = True
                        self.invalid_samples_left = self.n_pump_distrust


                    if response.find('Pump Off') > -1:
                        self.pump = False


                    for (var, value) in re.findall(r'([^=\t ]*)=([-0-9\.]+)', response):
                        if var == 't':
                            self.time = float(value)/(60*1000)

                        if var == 'temp':
                            temperature = float(value)

                        if var == 'I':
                            self.I = float(value)

                            if not isnan(self.I0) and self.I != 0:
                                self.OD = log10(self.I0/self.I)
                                new_sample_available = True

                        if var == 'f_stirrer':
                            self.stirrer_speed = float(value)
                            wx.CallAfter(self.m_txtStirrerSpeed.SetLabel, value)

                    if new_sample_available:
                        self.thread_lock.acquire()
                        if len(self.time_list) == 0:
                            self.starttime = self.time
                        self.time_list.append(self.time - self.starttime)
                        self.measurement_list.append(self.OD)

                        # -------- Kalman----------
                        # increase uncertainty after pumps
                        # print 'self.invalid_samples_left=', self.invalid_samples_left
                        sample_is_invalid = (0 < self.invalid_samples_left)
                        if sample_is_invalid:
                            self.P[0, 0] =  self.R / ((self.I*log(10))  )**2
                            self.P[1, 0] = 0
                            self.P[0, 1] = 0
                            self.x[0, 0] = log10( self.I0/self.I )
                            if self.pump == False:
                                self.invalid_samples_left -= 1


                        self.x, self.P, self.K = ekf(self.f, self.x, self.P, self.h, self.I, self.Q, self.R, I0=self.I0)     # ekf

                        # increase uncertainty if measurement and prediction differs greatly
                        if abs(self.I - self.h(self.x)) > 5*sqrt(self.R):
                            self.P[1, 0] = 0
                            self.P[0, 1] = 0
                            self.P[0, 0] = (self.x[0, 0]-log10(self.I0/self.I))**2

                        x             = self.x[0, 0]
                        geom_rate     = self.x[1, 0]
                        db_rate       = 3600 * log(geom_rate)/log(2)
                        var_x         = self.P[0, 0]
                        var_geom_rate = self.P[1, 1]
                        std_db_rate   = 3600*sqrt(var_geom_rate) / (log(2)*geom_rate)
                        self.uncertainty_list.append( var_x )
                        self.state_list.append(x)
                        self.dbrate_list.append(db_rate)
                        self.dbrate_uncertainty_list.append( std_db_rate )
                        self.thread_lock.release()

                        wx.CallAfter(self.plot)

                        logstring = '%.0f\t%.0f\t%f\t%f\t%f\t%f\t%f\t%.1f\t%.2f\n' % (self.time*60, self.I , self.OD, x, sqrt(var_x), db_rate, std_db_rate, self.stirrer_speed, temperature)
                        self.LogToCSVFile(logstring)
                        new_sample_available = False


                    #remove non printable characters like zeros
                    response_printable = filter(lambda x: x in string.printable, response)
                    sys.stdout.write(response)
                    self.LogToTxtFile(response_printable)
                    response = ''
                sleep(0.01)
            elif self.connecting:
                print 'connecting...'
                self.disconnect()
                sleep(1)
                self.connect(self.data_source)


        print 'self.threads', self.threads
        self.threads -= 1
        print 'self.threads', self.threads
        # except:
        #     self.OnConnect(None)

    def __del__(self):
        print 'done2: ' + str(self.done)
        # while self.threads > 0:
        #     pass
        if self.connected:
            self.ser.close()

def main():
    ex = wx.App()
    TurbidostatGUI(None)
    ex.MainLoop()

if __name__ == '__main__':
    main()
