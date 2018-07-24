#!/usr/local/bin/python3.6
import datetime
import epics
import numpy as np
import os
import picamera
import picamera.array
import time
import subprocess
import sys

from picamera_methods import *


os.environ['PYEPICS_LIBCA'] = "/home/epics/base/lib/linux-arm/libca.so"

# Timestamp
start_now = datetime.datetime.now()
path_time_prefix, pic_time_prefix = [start_now.strftime(pat) for pat in ["%y%m%d", "%y%m%d_%H%M_"]]

# Miscellanous
roi = [750, 2100, 2750, 500]  # [Left, Lower, Right, Upper]
pv_additionals = {}

#===========================================
#================== SINGLEPIC ==================
argv_range = len(sys.argv)
if not len(sys.argv) == 2:
    pic_name_save = input("Please name your picture, it will be prefixed by a timestamp: ")
else:
    pic_name_save = sys.argv[1]

# NO CHANGES necessary below this point
pic_name = pic_time_prefix + pic_name_save

# Confirmation dialog
print("Take one picture named: {}".format(pic_name))
confirmation = input("Do you want to continue? [Yy]")
if not any(confirmation == yes for yes in ['Y','y']):
    exit_script()
    
# Path
pic_path = make_dir('single', path_time_prefix, None)
print("Picture will be saved here: {}".format(pic_path))

# Overwrite dialog
if os.path.isfile(pic_path + pic_name + ".npz") or os.path.isfile(pic_path + pic_name + ".png"):
    overwrite = input("{}{} already exits. Do you want to overwrite it?".formate(pic_path, pic_name))
    if not overwrite == 'yes':
       exit_script()


# Miscellanous
pics_all = dict()

# Main
print("Stopping Webserver")
subprocess.call(['/home/pi/RPi_Cam_Web_Interface/stop.sh'])

try:
    print("Starting PiCamera")
    with picamera.PiCamera() as camera:
        with picamera.array.PiBayerArray(camera) as output:
            camera.start_preview()
            print("Waiting for camera to warm up: ", end='', flush=True)
            for i in range(20,0,-1):
                print("{:=02d}".format(i), end=' ', flush=True)
                time.sleep(0.1)
            print(" ")
            print("Taking Picture: {}".format(pic_name))
            camera.capture(output, 'jpeg', bayer=True)
            imgarray = roi_img(output.array, *roi)
            #imgarray = output.array
            now = datetime.datetime.now()
            plot_pic(pic_path, pic_name, imgarray, now)
            write_camtab(pic_path, pic_name, camera, camlist)
            save_to_npz(pic_path, pic_name, imgarray, now, camera, camlist)
    print("Stopping picamera", flush=True)
        
except:
    print("Error exception occured: Aborting")


print("Starting Webserver", flush=True)
subprocess.call(['/home/pi/RPi_Cam_Web_Interface/start.sh'])

