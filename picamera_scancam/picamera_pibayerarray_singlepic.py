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


os.environ['PYEPICS_LIBCA'] = "/home/epics/base/lib/linux-arm/libca.so"

# Changes only here
# Defaults
argv_range = len(sys.argv)
if not len(sys.argv) == 2:
    pic_name = input("Please name your picture, it will be prefixed by a timestamp: ")
else:
    pic_name = sys.argv[1]

# NO CHANGES necessary below this point
# Time of Measurement
start_now = datetime.datetime.now()
path_time_prefix, pic_time_prefix = [start_now.strftime(pat) for pat in ["%y%m%d", "%y%m%d_%H%M_"]]
pic_name_save = pic_time_prefix + pic_name + ".npz"

# Path
pic_path = "/home/pi/python/quadscan/single_pics/{}".format(path_time_prefix)
if not os.path.isdir(pic_path):
    print("Picture directory does not exist yet, making dir {}".format(pic_path))
    try:
        os.system("mkdir {}".format(pic_path))
    except:
        print("Could not make picture directory, aborting")
        sys.exit(0)

# Confirmation dialog
print("Take one picture named: {}".format(pic_name))
print("It will be saved here: {}".format(pic_path))
response = input("Do you want to continue? [Yy]")
if not any(response == yes for yes in ['Y','y']):
    print("Aborting.")
    sys.exit(0)


# Optional region of interest
def roi(x,p=0):
    roi_f = 800
    return int(round((x+(-1)**p*roi_f)/2))

# Camera
set_camera_options_dict = {'sensor_mode': 1, 'iso' : 0, 'framerate': 30, 'awb_mode' : 'off'}

def set_camera_options(cam):
    for k, v in set_camera_options_dict.items():
        setattr(cam, k, v)    

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
            #set_camera_options(camera)
            print("Waiting for camera to warm up: ", end='', flush=True)
            for i in range(20,0,-1):
                print("{:=02d}".format(i), end=' ', flush=True)
                time.sleep(0.1)
            print(" ")
            print("Ready to take pictures")

            # Camera attributes
            camera_attr = [attr for attr in dir(camera) if not attr.startswith("_") and not attr == 'preview']
            camera_attr_values = dict()
            for attr in camera_attr:
                try:
                    attr_value = getattr(camera, attr)
                    if not callable(attr_value): camera_attr_values[attr] = str(attr_value)
                except:
                    pass

            # Measurement loop
            pics_all['picamera_specs'] = camera_attr_values
            print("Taking Picture: {}".format(pic_name))
   
            camera.capture(output, 'jpeg', bayer=True)
            # yc,xc = output.array.shape[:2]
            # imgarray_roi = output.array[roi(yc,1):roi(yc),roi(xc,1):roi(xc),:]
            imgarray = output.array
            now = datetime.datetime.now()
            pics_all[pic_name] = {'img': imgarray, 'timestamp': now.strftime("%Y-%m-%d %H:%M:%S")}
                

except:
    print("Error exception occured: Aborting")

finally:
    # Save pictures
    outfile = "{}/{}".format(pic_path, pic_name_save)
    print("Pictures taken successfully, saving to: {}".format(outfile), flush=True)
    np.savez_compressed(outfile, **pics_all)

    print("Stopping picamera", flush=True)

    print("Starting Webserver", flush=True)
    subprocess.call(['/home/pi/RPi_Cam_Web_Interface/start.sh'])
    print("Don't forget to take a picture for scale")
