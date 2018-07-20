import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import QuadscanParabelFit as qp
#from matplotlib import rc

#plt.rc('text', usetex=True)
plt.rc('font', family='serif')
plt.rc('mathtext', fontset='stix')
#rc('font',**{'family':'serif','serif':['Helvetica']})


###  Hier bitte Pfade (path, path_info) und Element (el) auswählen ###
###  Eventuell skip_header beim Einlesen der Dateien ändern ###
###  Bei schlechten Fits eventuell die Grenzen ändern (startpar1, startpar2, startpar3) ###

path = '180720/180720_1112_wirescan.csv'
path_info = '180720/180720_1112_wirescan_info.dat'

#melba_020:trip_q1, melba_020:trip_q2, melba_020:trip_q3, melba_050:trip_q1, melba_050:trip_q2, melba_050:trip_q3
el = 2  # aktueller verwendeter Quadrupol
dBdsi = [0.474, 0.472, 0.40374, 0.472, 0.472, 0.472]  # dB/(ds*I) in T/(m*A)
l = [0.3979, 0.2659, 0.1339, 0.3575, 0.2255, 0.0935]  # Länge der Driftstrecke in m

ep = 895.394    # e/p in m/(Vs)
s = 0.04921     # effektive Länge in m
gamma = 1.196
beta = 0.5482

x_data, y_data = [], []
fitpar, fitcov, ksep, emittanz = [[], [], []], [[], [], []], [[], [], []], [[], [], []]
#fitpar, fitcov, ksep, emittanz = np.array([]), np.array([]), np.array([]), np.array([])
k = np.array([])

bkg = 0
ibkg = 0
ihilf = 0

startpar = [[[0, 30, 0], [65, 40, 3.4]], [[0, 80, 0], [65, 90, 3.4]], [[0, 103, 0], [65, 113, 3.4]]]

plt.figure(1)
#plt.rc('text', usetex=True)
#plt.rc('font', family='serif')

###Einlesen der Daten und umschreiben in Listen. Berechnung der k-Werte___________________________###

data = np.genfromtxt(path, delimiter=',', skip_header=1)  # , skip_footer=0, names=['l', 'x','y'])
info_data = np.genfromtxt(path_info, delimiter=",", skip_header=18)

for i in range(0, len(info_data)):
    x_data.append([])
    y_data.append([])

for i in range(0, int(info_data[0][3])):
    x_data[0].append(data[i][1] * 152.175 / (65536 - 1))
    y_data[0].append(data[i][2] * 0.001)

for j in range(1, len(info_data)):
    for i in range(int(info_data[j-1][3]), int(info_data[j][3])):
        x_data[j].append(data[i][1] * 152.175 / (65536 - 1))
        y_data[j].append(data[i][2] * 0.001)

for i in range(0, len(info_data)):  # Quadrupolstärken
    k = np.append(k, [[round(ep * dBdsi[el] * info_data[i][2], 2)]])

for i in range(0, len(info_data)):
    #print(len(info_data)-i-1, "________________________________")
    #print(len(x_data[len(info_data)-i-1]))
    #print(len(info_data))
    #print(len(x_data))
    if len(x_data[len(info_data)-i-1]) < 10000:
        #print("yes")
        #del x_data[i]
        #print("anfang ", len(x_data[:len(info_data)-i-1]))
        #print("ende ", len(x_data[len(info_data)-i:]))
        #print("gesamt ", len(x_data))
        x_data = x_data[:len(info_data) - i - 1] + x_data[len(info_data) - i:]
        y_data = y_data[:len(info_data) - i - 1] + y_data[len(info_data) - i:]
        k = np.delete(k, len(info_data)-i-1)

print("Es wurden ", len(info_data) - len(x_data), " Messungen gelöscht.")
#print(len(k))
#print(len(x_data))
#print(len(y_data))

print("Quadrupolstärken in 1/m^2: ", k)

for i in range(0, len(x_data)):
    for j in range(0, len(x_data[i])):
        if x_data[i][j] > 58 and x_data[i][j] < 62:
            bkg += y_data[i][j]
            ibkg += 1

bkg = bkg/ibkg
print("Der Untergrund ist ", bkg, " a.u. (Mittelung über ", ibkg, " Messpunkte)")

for i in range(0, len(y_data)):
    for j in range(0, len(y_data[i])):
        y_data[i][j] = y_data[i][j] - bkg

###Definitionen der Funktionen ___________________________________________________________________###

def gaus(x, a, x0, sigma):
    global offset
    return a * np.exp(-(x - x0) ** 2 / (2 * sigma ** 2))

def peakfit(fkt, x, y, startparameter, fitparameter, covarianz, kneu, fitnumber, peaknumber):
    global k
    global x_data
    popt, pcov = curve_fit(fkt, x, y, bounds=startparameter)
    plt.plot(x, fkt(x, popt[0], popt[1], popt[2]), color=(0, 0, fitnumber / len(x_data)))
    plt.subplot(212)
    plt.plot(x, fkt(x, popt[0], popt[1], popt[2]), color=(0, 0, fitnumber / len(x_data)))
    if (popt[0] < (startparameter[1][0] - 0.1)) and (popt[1] < (startparameter[1][1] - 0.1)) and (
            popt[1] > (startparameter[0][1] + 0.1)) and (popt[2] < (startparameter[1][2] - 0.1)):
        fitparameter.append(popt[2]/1000)
        covarianz.append(pcov[2][2]/1000)
        kneu.append(k[fitnumber])
    else:
        print("Fit ", fitnumber, " bei Peak ", peaknumber, " ist zu nah an den Fitgrenzen: ", popt)

###Ausführung der Gaußfits an die Daten_________________________________________________________###
for j in range(0, 3):
    for i in range(0, len(x_data)):
        plt.subplot(211)
        plt.grid(color='black', linestyle='--')
        plt.ylabel(r'Intensität (a.u.)', fontsize=16)
        plt.plot(x_data[i], y_data[i], marker='o', markersize=1, color=(i / len(info_data), 0, 0), label='k = ' + str(k[i]))
        #plt.legend(bbox_to_anchor=(1.01, 1), loc="upper left")
        try:
            peakfit(gaus, x_data[i], y_data[i], startpar[j], fitpar[j], fitcov[j], ksep[j], i, j+1)
        except:
            print("Fit ", i, " bei Peak ", j+1, " hat nicht funktioniert")

###Plots und Dateiausgabe_______________________________________________________________________###

plt.ylabel(r'Intensität (a.u.)', fontsize=16)
plt.xlabel(r'$s$ (mm)', fontsize=16)
#plt.xlabel(r'\textbf{time} (s)')
#plt.ylabel(r'\textit{voltage} (mV)',fontsize=16)
#plt.legend(bbox_to_anchor=(1.01, 1), loc="upper left")

plt.grid(color='black', linestyle='--')
plt.savefig(path[:-4] + '_data_qs.png', dpi=(200), bbox_inches='tight')
plt.show()

###Parabelfits ________________________________________________________________________________###

for j in range(0, 3):
    plt.errorbar(np.array(ksep[j]), np.array(fitpar[j]) ** 2 * 1000000, 2 * np.array(fitcov[j]) * np.array(fitpar[j]) * 1000000, marker='o', markersize=2, linestyle='--', mec='black',
                 color=((j + 1) / 3, 0, 0))
    emittanz[j] = qp.parfit(np.array(ksep[j]), np.array(fitpar[j]) ** 2, 2 * np.array(fitcov[j]) * np.array(fitpar[j]),  s, l[el])

emittanz = np.array(emittanz)
plt.savefig(path[:-4] + '_parabel.pdf', dpi=200, bbox_inches='tight')
plt.grid(color='black', linestyle='--')
plt.show()

###Output-Datei _________________________________________________________________________________###

np.savetxt(path[:-4] +".txt", [ksep[0], fitpar[0], fitcov[0], ksep[1], fitpar[1], fitcov[1], ksep[2], fitpar[2], fitcov[2], "emittanz, delta_emittanz in mm mrad; rechte Seite, linke Seite, Mittelwert", emittanz[0], emittanz[1], emittanz[2]], header="k in 1/m^2, sigma in m, delta sigma in m", fmt='%s')

