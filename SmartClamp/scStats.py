import matplotlib.pyplot as plt
import os
import sys
import numpy as np

homeFolder = os.path.expanduser("~")
logFileFolder = homeFolder + '/Smart-Clamp/logs/Archive/'

manual = False

while True:
    try:
        if manual:
            year = int(input("Enter The Year [XXXX]: "))
            month = input("Enter The Month [XX]: ")
            day = int(input("Enter The Day [XX]: "))
            hour = int(input("Enter The Hour [24h]: "))
            minute = int(input("Enter The Minute [XX]: "))
            second = int(input("Enter The Second [XX]: "))
            logFilePath = "{}{}-{}-{}_{}-{}-{}.csv".format(logFileFolder, year, month, day, hour, minute, second)
            print(logFilePath)
        else:
            logFilePath = logFileFolder + "LED_no_filter.csv"
        logFile = open(logFilePath,'r')
        graph_data = logFile.read()
        break
    except:
        print("Please enter valid values for a Logfile in the Archive")
        inp = input("Continue? (Y/N)\n>>    ").upper()
        if inp == "N":
            sys.exit()

lines = graph_data.split('\n')
del lines[0]
xs = []
ys = []
for line in lines:
    if len(line) > 1:
        time, Ia, LON, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, temp_ard, temp_mp = line.split('\t')
        xs.append(float(time))
        ys.append(float(Ia))

plotType = int(input("1) Scatter\n2) Error Histogram\n>>   "))

if plotType == 1:
    plt.plot(xs, ys, label="irradience")
    plt.xlabel("Time [s]")
    plt.ylabel("Irradience [W/m^2]")
    # plt.xlim(0, 3600)
    # plt.ylim(30, 110)
    # plt.xticks(np.arange(0, 3600, 600))
    # plt.yticks(np.arange(30, 110, 10))
    plt.title("Light Sensor Live Plot")
    plt.legend()
    plt.show()
elif plotType == 2:
    offset = int(input("please enter an offset [105]: "))
    tolerance = int(input("please enter a tolerance: "))
    errors = []
    for point in ys:
        point = offset - point
        if point > 3:
            errors.append(point)

    print("Error Frequency: ", len(errors)/len(ys))
    bins = [5, 10, 15 , 20, 25, 30, 40, 50, 60 , 60 , 70, 80, 90, 100]
    plt.hist(errors, bins, histtype='bar', rwidth=0.9)
    plt.xticks(np.arange(3, 69, 3))
    plt.yticks(np.arange(0, 25, 5))
    plt.xlabel("Intensity Drop")
    plt.ylabel("Frequency")
    plt.xlim(3, 69)
    plt.ylim(0, 25)
    plt.title("Error Histogram")
    plt.show()
