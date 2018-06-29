#!/usr/bin/python

import numpy as np
import scipy.odr as odr
import matplotlib.pyplot as plt

### _____________________Plot und Fit der Parabel__________________________###
### Bei schlechten bzw. neuen Fits jeweils start und end ändern, sowie die
### richtige Fitfunktion nehmen. Danach die Startparameter startpar ändern

def parfit(k, sig, delsig, s, l):
    global gamma
    global beta
    gamma = 1.196
    beta = 0.5482

    parfitpar, emittanz, delemittanz = np.array([]), np.array([]), np.array([])
    kl, kr, sigl, sigr, delsigl, delsigr = np.array([]), np.array([]), np.array([]), np.array([]), np.array(
        []), np.array([])
    # Erhöhen des 1. Parameters => steileren Kurve und das Minimum wird zur 0 verschoben
    # Erhöhen des 2. Parameters => Verschiebung des Minimums von der 0 weg und Verschiebung in negative y-Richtung
    # Erhöhen des 3. Parameters => Verschiebung in positive y-Richtung und Minimum wird leicht weg von der 0 geschoben
    # Parameter 4. und 5. sind fix
    startpar = [1, 1, 1, s, l]
    ifixb = [1, 1, 1, 0, 0]


    for i in range(0, len(k)):
        if k[i] < 0:
            kl = np.append(kl, [[k[i]]])
            sigl = np.append(sigl, [[sig[i]]])
            delsigl = np.append(delsigl, [[delsig[i]]])
        if k[i] > 0:
            kr = np.append(kr, [[k[i]]])
            sigr = np.append(sigr, [[sig[i]]])
            delsigr = np.append(delsigr, [[delsig[i]]])

    def fitfkt1(m, x):
        return m[0] * 1e-06 * (np.cos(m[3] * np.sqrt(x)) - m[4] * np.sqrt(x) * np.sin(m[3] * np.sqrt(x))) ** 2 + m[2] * 1e-06 * (
                    m[4] * np.cos(m[3] * np.sqrt(x)) + np.sqrt(1 / x) * np.sin(m[3] * np.sqrt(x))) ** 2 + 2 * m[1] * 1e-06 * (
                           np.cos(m[3] * np.sqrt(x)) - m[4] * np.sqrt(x) * np.sin(m[3] * np.sqrt(x))) * (
                           m[4] * np.cos(m[3] * np.sqrt(x)) + np.sqrt(1 / x) * np.sin(m[3] * np.sqrt(x)))

    def fitfkt2(m, x):
        return m[0] * 1e-06 * (np.cosh(m[3] * np.sqrt(x)) + m[4] * np.sqrt(x) * np.sinh(m[3] * np.sqrt(x))) ** 2 + m[2] * 1e-06 * (
                    m[4] * np.cosh(m[3] * np.sqrt(x)) + np.sqrt(1 / x) * np.sinh(m[3] * np.sqrt(x))) ** 2 + 2 * m[1] * 1e-06 * (
                           np.cosh(m[3] * np.sqrt(x)) + m[4] * np.sqrt(x) * np.sinh(m[3] * np.sqrt(x))) * (
                           m[4] * np.cosh(m[3] * np.sqrt(x)) + np.sqrt(1 / x) * np.sinh(m[3] * np.sqrt(x)))


    def fitparabel(fitfkt, kwerte, fitwerte, fehler, startwerte, seite):
        global gamma
        global beta

        if fitfkt == fitfkt1:
            c = "green"
        else:
            c = "blue"

        # fit_typ = 0
        # deriv = 1

        fkt = odr.Model(fitfkt)
        data = odr.Data(kwerte, fitwerte, we=1. / np.power(fehler, 2))
        # data = odr.RealData(kwerte, fitwerte, covy=fehler)
        try:
            odrparabel = odr.ODR(data, fkt, beta0=startwerte, ifixb=ifixb, maxit=1000)
            # odrparabel.set_job(fit_typ=fit_typ, deriv=deriv)
            odroutput = odrparabel.run()
            # odroutput.cov_beta = odroutput.cov_beta * (odroutput.res_var) #Nur wenn keine x Fehler berücksichtigt werden
            # uncertainty = np.sqrt(np.diagonal(odroutput.cov_beta))
            print("Beta: ", odroutput.beta, "Beta Std Error: ", odroutput.sd_beta)
            print("Vor dem Quadrupol: xrms = ", np.sqrt(odroutput.beta[0])*1000, " mm und x'rms = ",
                  np.sqrt(np.abs(odroutput.beta[2])) * 1000, " mrad")
            print("Residual Variance: ", odroutput.res_var)
        except:
            print("Fit aus ", seite, " Teil der Parabel konnte nicht erstellt werden.")
            return 0, 0
        else:
            plt.xlabel("k (1/m^2)", fontsize=16)
            plt.ylabel("sig^2 (mm^2)", fontsize=16)
            if seite == "rechtem":
                plt.plot(kwerte, fitfkt([odroutput.beta[0], odroutput.beta[1], odroutput.beta[2], s, l], kwerte)*1000000, color=c)
            else:
                plt.plot(-kwerte, fitfkt([odroutput.beta[0], odroutput.beta[1], odroutput.beta[2], s, l], kwerte)*1000000, color=c)
            if (odroutput.beta[0] * odroutput.beta[2] - odroutput.beta[1]*odroutput.beta[1]) > 0:
                eps = beta * gamma * np.sqrt(odroutput.beta[0] * odroutput.beta[2] - odroutput.beta[1] * odroutput.beta[1])
                return eps, beta * gamma *np.sqrt((odroutput.beta[2]*odroutput.sd_beta[0])**2 + (odroutput.beta[0]*odroutput.sd_beta[2])**2 + (2*odroutput.beta[1]*odroutput.sd_beta[1])**2) /(2*eps)
            else:
                print("Emittanz aus ", seite, " Teil der Parabel ist imaginär.")
                return 0, 0

    if k[np.where(sig == np.amin(sig))[0][0]] < 0:
        print("Minimum liegt im negativem Bereich __________________________________________________")
        # Rechte Seite der Parabel ____________________________________________________________
        emittanz = np.append(emittanz, [[fitparabel(fitfkt2, kr, sigr, delsigr, startpar, "rechtem")]])
        # Linke Seite der Parabel
        emittanz = np.append(emittanz, [[fitparabel(fitfkt1, -kl, sigl, delsigl, startpar, "linken")]])
    else:
        print("Minimum liegt im positivem Bereich __________________________________________________")
        # Rechte Seite der Parabel ____________________________________________________________
        emittanz = np.append(emittanz, [[fitparabel(fitfkt1, kr, sigr, delsigr, startpar, "rechtem")]])
        # Linke Seite der Parabel
        emittanz = np.append(emittanz, [[fitparabel(fitfkt2, -kl, sigl, delsigl, startpar, "linken")]])

    print("Die Emittanzen sind: ", emittanz[0], ", ", emittanz[2], ".")
    print("Der Mittelwert ist: ", (emittanz[0] + emittanz[2]) / 2, ".")

    emittanz = np.append(emittanz, [(emittanz[0] + emittanz[2]) / 2, np.sqrt(emittanz[1]**2+emittanz[3]**2)/2])

    return emittanz


if __name__ == "__main__":
    import sys

    parfit(sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
