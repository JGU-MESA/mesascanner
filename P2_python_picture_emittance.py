# coding: utf-8

import datetime
import glob
import python_method_analysis as pma
import python_method_QuadscanParabelFit as pmqp
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import pandas as pd
import re
import os
import sys

from matplotlib import colors as mcolors

##########################################################################

pic_dir  = "..\\All_quadscan\\" + sys.argv[1] + "\\" + sys.argv[2] + "\\"
measure_time = sys.argv[3]
## Limits for fitting; None == min or max of k
limits = {'xleft': None, 'xright': None, 'yleft': None, 'yright': None}

##########################################################################

measure_timestamp = "{}_{}".format(pic_dir[-7:-1], measure_time)
pic_path = pic_dir + measure_timestamp + "/"
infile = glob.glob(pic_path + "*result_DataFrame.dat")[0]

# Load results
try:
    headers = ','.join(pma.find_headers(infile))
    df = pd.read_csv(infile, comment='#', index_col=0)
except:
    print("Could not find dataframes or read headers.")
    print("Aborting.")
    sys.exit()

# Beam current information
try:
    Ibd = re.findall(pma.ibdpattern, headers)[0]
    ibd_num = [float(num) for num in re.findall(pma.renum, Ibd)[:2]]
    if not Ibd[:3] == 'Ibd':
        Ibd = 'Ibd = NA'
except:
    print("Could not determine Ibd")
    Ibd = 'Ibd = NA'
    ibd_num = [None, None]

try:
    trip_no = int(re.findall(r't\d+', infile[len(pic_path):])[0][1:])
    quad_no = int(re.findall(r'q\d+', infile[len(pic_path):])[0][1:])
except:
    print("Could not assign trip_no or quad_no from {}".format(infile[len(pic_path):]))
    sys.exit()

# Sub roi for fitting
kall = df['k[1/m2]']
## x
if limits['xleft'] == None:
    xleft = np.min(kall)
else:
    xleft = limits['xleft']
if limits['xright'] == None:
    xright = np.max(kall)
else:
    xright = limits['xright']
    
## y
if limits['yleft'] == None:
    yleft = np.min(kall)
else:
    yleft = limits['yleft']
if limits['yright'] == None:
    yright = np.max(kall)
else:
    yright = limits['yright']
    
# Assign for fit
k = df['k[1/m2]']
sigx, sigxerr = df['sigma_x[mm]']/1000, df['sigma_x_err[mm]']/1000  # Sigma in m
sigx.name, sigxerr.name = sigx.name[:-4] + "[m]", sigxerr.name[:-4] + "[m]"
sigy, sigyerr = df['sigma_y[mm]']/1000, df['sigma_y_err[mm]']/1000
sigy.name, sigyerr.name = sigy.name[:-4] + "[m]", sigyerr.name[:-4] + "[m]"

## Sub_roi
xlimit, ylimit = (xleft <= k) & (k <= xright), (yleft <= k) & (k <= yright)
kx, ky = k[xlimit], k[ylimit]
sigxx, sigxxerr = sigx[xlimit], sigxerr[xlimit]
sigyy, sigyyerr = sigy[ylimit], sigyerr[ylimit]

# Fit
print("Try fitting x")
resx = pmqp.parfit(kx, sigxx**2, sigxxerr**2, pma.s, pma.l[trip_no][quad_no])
print("Try fitting y")
resy = pmqp.parfit(ky, sigyy**2, sigyyerr**2, pma.s, pma.l[trip_no][quad_no])

## Fit results
epsxl, epsxr = [resx['epsl'], resx['depsl']], [resx['epsr'], resx['depsr']]
epsyl, epsyr = [resy['epsl'], resy['depsl']], [resy['epsr'], resy['depsr']]
mean_epsx = [resx['mean_eps'], resx['dmean_eps']]
mean_epsy= [resy['mean_eps'], resy['dmean_eps']]


# Result path
outfile = infile[:len(pic_path)] + measure_timestamp + "_" + infile[len(pic_path):-4] + "_emittance"
if os.path.isfile(outfile + ".pdf") or os.path.isfile(outfile + ".png"):
    overwrite = input("{} already exists, do you want to overwrite it?[yes, please]\nIt will be postfixed by timestamp instead.")
    if overwrite  != 'yes, please':
        now = datetime.datetime.now()
        postfix = now.strftime("%y%m%d_%H%M")
        outfile =  infile[:-4] + "_emittance_{}".format(postfix)

# Save results
result_npz = {'measure_timestamp': measure_timestamp, 'ibd[A]' : ibd_num, 'resx': resx, 'resy': resy}
np.savez_compressed(outfile + '.npz', **result_npz)

# Plot
## Figure and axes
fig, ax = plt.subplots(figsize = (12,8))
ay = ax.twinx()

## Fonts
font = {'family' : 'sans-serif',
        'size'   : 11}
mpl.rc('font', **font)

## Colors    
colors = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)
c = {'x':'red', 'xr': 'orange', 'xl': colors['orangered'], 'y':'blue', 'yr':'cyan', 'yl':colors['royalblue']}
ay.spines['left'].set_color(c['x'])  # twinx overwrites ax.spines
ay.spines['right'].set_color(c['y'])
ax.tick_params(axis='y', colors=c['x'])
ay.tick_params(axis='y', colors=c['y'])

## Title, labels and tics
ax.set_title("Emittance measurement: {}".format(infile))
ax.set_xlabel(r'$k$ [m$^{-2}$]')
ax.set_ylabel(r'$\sigma_x$ [mm$^{2}$]', color=c['x'])
ay.set_ylabel(r'$\sigma_y$ [mm$^{2}$]', color=c['y'])


info_text = Ibd + "\n"
if not mean_epsx == 0:
    info_text = info_text + r'$\varepsilon_{{n,rms,x}} = ({:.4f} +/- {:.4f})$ um'.format(*mean_epsx) + "\n"
else:
    info_text = info_text + r'$\varepsilon_{{n,rms,x}} = $ NA' + "\n"
if not mean_epsy == 0:
    info_text = info_text + r'$\varepsilon_{{n,rms,y}} = ({:.4f} +/- {:.4f})$ um'.format(*mean_epsy) 
else:
    info_text = info_text + r'$\varepsilon_{{n,rms,y}} = $ NA'

fig.text(0.01, 0.01, info_text, fontsize = 12)
    
ln = []

## Data
ln.append(ax.errorbar(k, sigx**2*1e6, yerr=sigxerr**2*1e6, fmt=c['x'][0]+'o', ecolor=c['x'], mfc=c['x'], mec='black', label='x'))
ln.append(ay.errorbar(k, sigy**2*1e6, yerr=sigyerr**2*1e6, fmt=c['y'][0]+'^', ecolor=c['y'], mfc=c['y'], mec='black', label='y'))

## left fits
if not resx['fitted_sigmasql'].size == 0:
    ln.append(ax.plot(kx[kx<0], resx['fitted_sigmasql']*1e6, '--', marker=None, color=c['xl'], label='x-fit (left)'))
if not resy['fitted_sigmasql'].size == 0:
    ln.append(ay.plot(ky[ky<0], resy['fitted_sigmasql']*1e6, ':', marker=None, color=c['yl'], label='y-fit (left)'))

## right fits
if not resx['fitted_sigmasqr'].size == 0:
    ln.append(ax.plot(kx[kx>0], resx['fitted_sigmasqr']*1e6, '-.',  marker=None, color=c['xr'], label='x-fit (right)'))
if not resy['fitted_sigmasqr'].size == 0:
    ln.append(ay.plot(ky[ky>0], resy['fitted_sigmasqr']*1e6, '-', marker=None, color=c['yr'], label='y-fit (right)'))

## Shrink plot by X% to put legend below
box = ax.get_position()
shrink_factor = 0.05
ax.set_position([box.x0, box.y0 + box.height * shrink_factor,
                 box.width, box.height * (1-shrink_factor)])
ay.set_position([box.x0, box.y0 + box.height * shrink_factor,
                 box.width, box.height * (1-shrink_factor)])

## Legend
labs = []
for i,itm in enumerate(ln):
    if type(itm) == list:
        labs.append(itm[0].get_label())
        ln[i]=itm[0]
    else:
        labs.append(itm.get_label())

leg = ax.legend(ln, labs, fontsize=font['size'], loc='upper right', bbox_to_anchor=(1, -2*shrink_factor), prop = {'size': 9},
          fancybox=True, shadow=True, ncol=7)

fig.savefig(outfile + ".png")
fig.savefig(outfile + ".pdf")
plt.show()