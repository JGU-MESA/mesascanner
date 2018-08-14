# coding: utf-8

"""
    This script fits a 2d gaussian distribution to all qd<quad_no>_<i_set>mA.npz files in pic_dir + path.
    It saves its result as dataframe and png
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


print("Running {}".format(sys.argv[0]))
# Defaults
annotations = []
##########################################################################
##########################################################################

pic_dir  = "..\\All_quadscan\\" + sys.argv[1] + "\\" + sys.argv[2] + "\\"
measure_time = sys.argv[3]

##########################################################################
##########################################################################

# Start angle for first fit (going from negativ to positiv, e.g. -200mA, -180mA..., 0mA, ... +200mA)
theta_deg = input("Start angle in degree: ")
try:
    theta_deg = float(theta_deg)
except:
    theta_deg = 0.0
    print("Could not read input, start fitting with angle {}".format(theta_deg))

# Miscellanous
measure_timestamp = "{}_{}".format(pic_dir[-7:-1], measure_time)
pic_path = pic_dir + measure_timestamp + "\\"
bckg = 'background.npz'
if 'triggered' in pic_dir:
    triggered = True

# Beamtime file
beamtimefile = pic_dir + pic_dir[-7:-1] + "_beamtime.txt"
ibd, amp = pma.read_beamtimefile(beamtimefile, measure_time)
if ibd == None or amp == None:
    print("Aborting")
    sys.exit()

# Annotations    
annotations = ["Ibd = {}".format(ibd), "Amp = {}".format(amp)]
try:
    annotations += ['px2mm = {:.6f}'.format(pma.px2mm)]
except:
    print("No scale factor 'px2mm' given, although needed.")
    print("Aborting.")
    sys.exit()

# Number of images to fit without background image 
pics = [pic for pic in glob.glob(pic_path + "*mA.npz")]
pics = [pic for pic in pics if not pic[len(pic_path):].startswith("fit_")]
pics = [pic for pic in pics if not pic[len(pic_path):].startswith("err_")]
nelm = len(pics)  

# Prepare result dataframes
## Pictures
dp = pd.DataFrame(columns=['curr_set[mA]', 'picture'])
idp = 0
for pic in pics:
    try:
        curr_set_pic = int(pic[-11:-6])
        trip_no = int(pic[len(pic_path):][3:6])
        quad_no = int(pic[len(pic_path):][7])
    except:
        print("Could not extract set current and quad number from filename! Use scheme: qd<quad_no>s_<:=+4d>mA.npz")
        sys.exit()
    else:
        dp.loc[idp] = [curr_set_pic, pic]
        idp +=1
dp = dp.sort_values(['curr_set[mA]'], ascending = True)
dp = dp.reset_index(drop=True)

## Results
df_result = pd.DataFrame(columns = ['pic', 'curr_get[A]', 'k[1/m2]', 'sigma_x[px]', 'sigma_x_err[px]', 
                                            'sigma_y[px]', 'sigma_y_err[px]', 'theta[rad]', 'theta_err[rad]'])

df_result_rms = pd.DataFrame(columns = ['pic', 'curr_get[A]', 'k[1/m2]', 'sigma_x[px]', 'sigma_x_err[px]', 
                                            'sigma_y[px]', 'sigma_y_err[px]', 'theta[rad]', 'theta_err[rad]'])
idx = 0

# Estimated time start
start_start =tm.time()

# Background image for substraction
try:
    print("Loading background image: {}{}".format(pic_path, bckg))
    img_bckg, time_bckg, curr_bckg = pma.load_image(pic_path, bckg)
    img_bckg = pma.roi_img(img_bckg, *pma.sub_roi)
except:
    print("Error while reading background image.")
    answer = input("Do you want to continue?[yes]")
    if not answer == 'yes':
        print("Aborting")
        sys.exit()


theta = np.deg2rad(theta_deg)  # From here on calculating in radians
for i, f in dp.iterrows():
    f = f['picture']
    i+=1 
    pic = f[len(pic_path):]
    
    if not pic == bckg and not pic.startswith("fit_*"): 
        start = tm.time()
                
        result_path = "{}fit_{}".format(pic_path, pic[:-4])
        result_plot_path = result_path + ".png"
        
        pma.printeq()
        print("Loading {}/{}: {}{}".format(i, nelm, pic_path, pic))
        img, time_img, curr_get = pma.load_image(pic_path, pic)
        img = pma.roi_img(img, *pma.sub_roi)

        print("Subtracting background from image")
        img_wob = pma.subtract_background(img, img_bckg)
        try:
            print("Start fitting subtracted image")
            res = pma.two_dim_gaussian_fit(img_wob, pic, theta)
        except:
            print("Could not fit {}".format(pic))
        
        else:
            print("Finished! Saving plot: {}".format(result_plot_path))
     
            theta = res['img_popt'][-1]

            sigmax, sigmax_err = res['img_popt'][3], np.sqrt(res['img_pcov'][3,3])
            sigmay, sigmay_err = res['img_popt'][4], np.sqrt(res['img_pcov'][4,4])
            theta_res, theta_res_err = res['img_popt'][-1], np.sqrt(res['img_pcov'][-1,-1])
        
            pma.plot_image_and_fit(pic, res['img'], res['img_fit'], result_plot_path, 
                time_img, curr_get, sigmax, sigmax_err, sigmay, sigmay_err)
            
            pma.save_result(pic[:-4], res, curr_get, result_path)
        
            k = pma.curr2k(curr_get, quad_no)
            df_result.loc[idx] = [pic, curr_get, k, sigmax, sigmax_err, sigmay, sigmay_err, theta_res, theta_res_err]
            idx +=1
        
        stop = tm.time()
        ert = (stop - start)*(nelm - i)
        print("Done! Estimated remaining time: {:.2f}".format(ert))
        start = tm.time()

stop_stop = tm.time()
pma.printeq()
print("Calculation took {:.3f}s".format(stop_stop-start_start))
pma.printeq()

# DataFrame post processing
df_result = df_result.sort_values(['curr_get[A]'], ascending=True)
df_result = df_result.reset_index(drop=True)
for col in df_result.columns:
    if col.endswith('[px]'):
        df_result[col[:-4] +'[mm]'] = pd.Series(pma.px2mm*df_result[col], index=df_result.index)


# Save result
outfile = pic_path + "qdt{:03d}q{}_result_DataFrame.dat".format(trip_no, quad_no)
if os.path.isfile(outfile):
    overwrite = input("{} already exists, do you want to overwrite it?[yes, please]\nIt will be prefixed by timestamp instead.")
    if overwrite  != 'yes, please':
        now = datetime.datetime.now()
        overwrite_prefix = now.strftime("%y%m%d_%H%M_")
        outfile =  pic_path + "{}_qdt{:03d}q{}_result_DataFrame.dat".format(overwrite_prefix, trip_no, quad_no)
        
info_text = ', '.join([ "Measured  {}".format(measure_timestamp),  
                                "scale px2mm =  {:.6f} mm/px".format(pma.px2mm), 
                                *annotations, "trip_no = {}".format(trip_no), "quad_no = {}".format(quad_no)])

with open(outfile, 'w') as f:
    f.write("#{}\n".format(info_text))
    df_result.to_csv(f, float_format='%11.3e')

# Plot
x = df_result['curr_get[A]']
y1 = df_result['sigma_x[px]']**2
y1err = df_result['sigma_x_err[px]']**2
y2 = df_result['sigma_y[px]']**2
y2err = df_result['sigma_y_err[px]']**2

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

#DEBUG
fig2, ax1 = plt.subplots(figsize = (11.7,8.3))

ax1.set_xlabel("Quadrupol current [A]", fontsize = 16)
ax1.set_ylabel(r'$\sigma^2$ [px]', fontsize = 16)
ax1.errorbar(x, y1, yerr=y1err, label="x", marker='o', linestyle='--', color = 'red', mfc='red', mec='black', ecolor='red')
ax1.errorbar(x, y2, yerr=y2err, label="y", marker='^', linestyle='-.', color = 'blue', mfc='blue', mec='black', ecolor='blue')

#ax1.grid()

y2_tick = np.arange(-360, 360+45, 45)
ytheta = np.rad2deg(df_result['theta[rad]'])
ax2 = ax1.twinx()
ax2.plot(x, ytheta, 'g-', marker = '*')
ax2.set_yticks(y2_tick)
ax2.set_ylabel(r'$\theta$ [$\degree$]', fontsize = 16)
ax2.grid()
fig2.text(0.01,0.01, info_text)
ax1.legend()
plt.savefig(outfile[:-4] + "_theta.png")
plt.show()