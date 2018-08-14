# coding: utf-8

"""
    This script copies refitted files from single to the 
"""


import datetime
import glob
import python_method_analysis as pma
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time as tm
import os
import sys

from shutil import copy2

##########################################################################
##########################################################################

pic_dir  = "..\\All_quadscan\\" + sys.argv[1] + "\\" + sys.argv[2] + "\\"
measure_time = sys.argv[3]

in_folder = "single\\"


##########################################################################
##########################################################################

# Outfile
measure_timestamp = "{}_{}".format(pic_dir[-7:-1], measure_time)
pic_path = pic_dir + measure_timestamp + "/"
outfile = glob.glob(pic_path + "*result_DataFrame.dat")[0]
# Infile
pic_in_path = pic_dir + "{}_{}".format(pic_dir[-7:-1], in_folder)
try:
    infile = glob.glob(pic_in_path + "*result_DataFrame.dat")[0]
except:
    print("No infile found in: {}".format(pic_in_path))
    sys.exit()

# Load results
try:
    headers = pma.find_headers(outfile)
    df = pd.read_csv(outfile, comment='#', index_col=0)
    df_in = pd.read_csv(infile, comment='#', index_col=0)
except:
    print("Could not find dataframes.")
    print("Aborting.")
    sys.exit()

# Confirmation
answer = input("You are about to merge {} into {}. Do you want to continue?[yes]".format(infile, outfile))
if not answer == 'yes':
    print("Aborting")
    sys.exit()

# Info text
info_text = ', '.join(headers)
    
# Merge
for idx, row in df_in.iterrows():
    df_index = df[df['pic']==row['pic']].index[0]
    if not all(df.iloc[df_index] == row):
        print("Overwriting index {}".format(df_index))
        df.iloc[df_index] = row

# (Over-)Write new Dataframe
with open(outfile, 'w') as f:
    f.write("#{}\n".format(info_text))
    df.to_csv(f, float_format='%11.3e')
    
# Copy png files from in to out
print("Copying fit_*.png from {} to {}".format(pic_in_path, pic_path))
fits = [fit for fit in glob.glob(pic_in_path +"*") if fit[len(pic_in_path):].startswith("fit_")]

for fit in fits:
    print("Copying {} to {}".format(fit, pic_path))
    copy2(fit, pic_path)

    
# Plot
x = df['curr_get[A]']
y1 = df['sigma_x[px]']**2
y1err = df['sigma_x_err[px]']**2
y2 = df['sigma_y[px]']**2
y2err = df['sigma_y_err[px]']**2

fig, ax1 = plt.subplots(figsize = (11.7,8.3))

ax1.set_xlabel("Quadrupol current [A]", fontsize = 16)
ax1.set_ylabel(r'$\sigma^2$ [px]', fontsize = 16)
ax1.errorbar(x, y1, yerr=y1err, label="x", marker='o', linestyle='--', color = 'red', mfc='red', mec='black', ecolor='red')
ax1.errorbar(x, y2, yerr=y2err, label="y", marker='^', linestyle='-.', color = 'blue', mfc='blue', mec='black', ecolor='blue')
ax1.legend()
ax1.grid()

ax2 = ax1.twinx()
ax2.set_ylim(np.array(ax1.get_ylim())*pma.px2mm**2)
ax2.set_ylabel(r'$\sigma^2$ [mm$^2$]', fontsize = 16)

fig.text(0.01,0.01, info_text)
ax1.legend()
plt.savefig(outfile[:-4] + ".png")

# Theta
fig2, ax1 = plt.subplots(figsize = (11.7,8.3))

ax1.set_xlabel("Quadrupol current [A]", fontsize = 16)
ax1.set_ylabel(r'$\sigma^2$ [px]', fontsize = 16)
ax1.errorbar(x, y1, yerr=y1err, label="x", marker='o', linestyle='--', color = 'red', mfc='red', mec='black', ecolor='red')
ax1.errorbar(x, y2, yerr=y2err, label="y", marker='^', linestyle='-.', color = 'blue', mfc='blue', mec='black', ecolor='blue')

y2_tick = np.arange(-360, 360+45, 45)
ytheta = np.rad2deg(df['theta[rad]'])
ax2 = ax1.twinx()
ax2.plot(x, ytheta, 'g-', marker = '*')
ax2.set_yticks(y2_tick)
ax2.set_ylabel(r'$\theta$ [$\degree$]', fontsize = 16)
ax2.grid()
fig2.text(0.01,0.01, info_text)
ax1.legend()
plt.savefig(outfile[:-4] + "_theta.png")
plt.show()