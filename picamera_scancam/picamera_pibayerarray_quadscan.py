#!/usr/local/bin/python3.6
import sys

if sys.argv[1] == 'help':
    print("Usage: python3 {} <quad_no=1> <i_init=-0.05> <i_final=0.15> <di=0.05>".format(sys.argv[0])) 
    sys.exit()

import datetime
import epics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os
import picamera
import picamera.array
import time
import subprocess

from fractions import Fraction
from picamera_methods import *


os.environ['PYEPICS_LIBCA'] = "/home/epics/base/lib/linux-arm/libca.so"

# Timestamp
start_now = datetime.datetime.now()
path_time_prefix, pic_dir = [start_now.strftime(pat) for pat in ["%y%m%d", "%y%m%d_%H%M"]]

# Miscellanous
roi = [750, 2100, 2750, 500]  # [Left, Lower, Right, Upper]
pv_additionals = {}

#===========================================
#================== QUADSCAN ==================   
# Default Quadrupol parameter
quad_no = 1
i_init = -0.05  # Current in mA
i_final = 0.15  # Current in mA
di = 0.05

#PVs
pv_qd_param = ['i_set', 'i_get', 'on_set']
pv_additional =['steam:laser:setamp_get', 'steam:powme1:pow_get']
pv_all = dict()
for qd_param in pv_qd_param:
    pv_all[qd_param] = epics.PV('melba_020:trip_q{}:{}'.format(quad_no, qd_param))

# Arguments
argv_range = len(sys.argv)
if 1 < len(sys.argv):
    try:
        quad_no = int(sys.argv[1])
        i_init = float(sys.argv[2])
        i_final = float(sys.argv[3])
        di = abs(float(sys.argv[4]))
    except:
        pass

if i_init > i_final:
    di = -di
nelm = int((i_final + di - i_init)/di)

# Confirmation dialog
print("This script scans through quadrupol melba_020:trip_q{}.".format(quad_no))
print("It ramps current from {} to {} with stepwidth {} <=> {} pictures.".format(i_init, i_final, di, nelm))
print("It takes a picture for each current and saves them seperately in an .npz-file and .png-file.")
confirmation = input("Do you want to continue? [Yy]")
if not any(confirmation == yes for yes in ['Y','y']):
    print("Aborting.")
    sys.exit(0)

print("Prepare: HV Voltage and laser amplitude (Attention: not to high as for screen gets destroyed!)")
print("Prepare: Drive screen in beamline")
print("Prepare: Deactivate all following magnetic devices after the selected quadrupol.")
print("Laser shutter will be opened by script")
response = input("Ready? [Gg]")
if not any(response == yes for yes in ['G','g']):
    print("Aborting.")
    sys.exit(0)

# Path
make_dir('quad', path_time_prefix, pic_dir)

# Main
print("Stopping Webserver")
subprocess.call(['/home/pi/RPi_Cam_Web_Interface/stop.sh'])

print("Open shutter")
epics.caput("steam:laser_shutter:ls_set", 1)

try:
    print("Starting PiCamera")
    with picamera.PiCamera() as camera:
        with picamera.array.PiBayerArray(camera) as output:
            camera.start_preview()
            camera.sensor_mode = 2
            camera.framerate = 30
            camera.exposure_mode = 'auto'
            camera.shutter_speed= 0
            print("Waiting for camera to warm up: ", end='', flush=True)
            for i in range(20,0,-1):
                print("{:=02d}".format(i), end=' ', flush=True)
                time.sleep(0.1)
            print(" ")
            print("Ready to take pictures")
    
    
            # Measurement loop
            for i_set in np.round(np.linspace(i_init, i_final, nelm),6):
                # Time estimation
                if i_set == i_init:
                    start = time.time()
                if i_set > i_init:
                    stop = time.time()
                    no_steps = (i_final+di-i_set)/di
                    print("Estimated remaining time: {:.3f}s".format(no_steps*(stop-start)), end="; ", flush=True)
                    start = time.time()
    
                # Quadrupol
                pv_all['i_set'].put(i_set)
                time.sleep(10) # i_get is scanned every 10s
    
                # Take picture
                pic_name = "qd{}s_{:=+05d}mA".format(quad_no, int(i_set*1000))
                print("Taking Picture: {}".format(pic_name))
                camera.capture(output, 'jpeg', bayer=True)
                
                # Image processing
                ## Region of Interest
                imgarray = roi_img(output.array, *roi)
                # imgarray = output.array
                now = datetime.datetime.now()
                i_get = round(pv_all['i_get'].get(),6)
                pv_additional_info(pv_additionals, pv_list)
    
                plot_pic(pic_path, pic_name, imgarray, now)
                write_camtab(pic_path, pic_name, camera, camlist)
                save_to_npz(pic_path, pic_name, imgarray, now, camera, camlist, i_set, i_get, pv_additionals)
                
    
            #Background image
            pic_name = "background"
            print("Taking background image", flush=True)
            print("Closing shutter")
            epics.caput("steam:laser_shutter:ls_set", 0)
            time.sleep(1)
            camera.capture(output, 'jpeg', bayer=True)
            ## Region of Interest
            bckgrd_array = roi_img(output.array, *roi)
            #bckgrd_array = output.array
            bckgrd_now = datetime.datetime.now()
            plot_pic(pic_path, pic_name, bckgrd_array, now)
            write_camtab(pic_path, pic_name, camera, camlist)
            save_to_npz(pic_path, pic_name, bckgrd_array, bckgrd_now, camera, camlist, 0, 0)
                
except:
    print("Error exception occured: Aborting")


print("Stopping picamera")
# ===== Start Webserver =====
print("Starting Webserver", flush=True)
subprocess.call(['/home/pi/RPi_Cam_Web_Interface/start.sh'])

print("Done")
print("Don't forget to take a picture for scale")
