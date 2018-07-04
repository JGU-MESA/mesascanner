#!/usr/local/bin/python3.6
import sys

if sys.argv[0] == 'help':
    print("Usage: python3 {} <number> <save_name|quad_no>".format(sys.argv[0]))
    sys.exit()

import datetime
import RPi.GPIO as GPIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os
import picamera
import picamera.array
import time
import subprocess
import sys

from fractions import Fraction
from picamera_methods import *


try:
    import epics
    os.environ['PYEPICS_LIBCA'] = "/home/epics/base/lib/linux-arm/libca.so"
except:
    pass


# Timestamp
start_now = datetime.datetime.now()
path_time_prefix, pic_dir = [start_now.strftime(pat) for pat in ["%y%m%d", "%y%m%d_%H%M"]]

# Camera attributes to save
camlist = ['sensor_mode', 'iso', 'shutter_speed', 'exposure_mode', 
                'awb_mode', 'awb_gains', 'framerate', 'digital_gain', 'analog_gain', 'revision', 'exposure_speed']

# PVs to save (for all shots) (already defined in picamera_methods, optional)
# pv_list = ['steam:laser:setamp_get', 'steam:laser:pl_get', 'steam:powme1:pow_get']

# Miscellanous
pv_additionals = {}
res_time = []
    
# Arguments
try:
    num_of_pics = int(sys.argv[1])
    try:
        quad_no = int(sys.argv[2])
        pic_name_save = None
    except:
        quad_no = None
        pic_name_save = sys.argv[2]

except:
    print("Usage: python3 {} <number> <save_name|quad_no>".format(sys.argv[0]))
    exit_script(False)

# Path
pic_path = "/home/pi/python/quadscan/oneshot_pics/{}/{}".format(path_time_prefix, pic_dir)
if not os.path.isdir(pic_path):
    print("Picture directory does not exist yet, making dir {}".format(pic_path))
    try:
        os.system("mkdir -p {}".format(pic_path))
        with open("{}/cam_tab.txt".format(pic_path), 'a') as f:
            f.write("pic_name\t")
            for k in camlist:
                f.write("{}\t".format(k))
            f.write("\n")
    except:
        print("Could not make picture directory, aborting")
        exit_script(False)

#PVs for saving quadrupol current
try:
    quad_i_get = epics.PV("melba_020:trip_q{:1d}:i_get".format(quad_no))
    quad_i_set = epics.PV("melba_020:trip_q{:1d}:i_set".format(quad_no))
except:
    print("No quadrupol number was given or pvs could not be assigned")
    quad_i_get, quad_i_set = None, None


# GPIO 
GPIO.setmode(GPIO.BOARD) 
if GPIO.getmode() == 10:
    p_trig = 12
GPIO.setup(p_trig, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Triggerpin by default on 0V


# Confirmation dialog
print("Take {} picture named: {}".format(num_of_pics, pic_name_save))
print("It will be saved here: {}".format(pic_path))
try:
    response = input("Do you want to continue? [Yy,b = only background image]")
    if not any(response == yes for yes in ['Y','y', 'b']):
        exit_script()
        
    # No trigger for background picture 'b'
    if response == 'b':
        background = True
    else:
        background = False
except KeyboardInterrupt:
    exit_script()
    
print("________________________________________")

# ===== Stop Webserver =====
print("Stopping Webserver")
subprocess.call(['/home/pi/RPi_Cam_Web_Interface/stop.sh'])

print("Starting PiCamera")
with picamera.PiCamera() as camera:
    with picamera.array.PiBayerArray(camera) as output:
        # Camera settings
        ## https://picamera.readthedocs.io/en/release-1.13/recipes1.html#capturing-consistent-images
        # ============================    
        camera.start_preview()
        camera.sensor_mode = 2
        camera.framerate = 1
        time.sleep(1)
        camera.shutter_speed = 1000000
        camera.exposure_mode = 'auto'
        camera.iso = 800
        # ============================    
        print("Waiting for camera to setup:")
        #for i in range(30, -1, -1): # Best is to wait 30s
        for i in range(10, -1, -1): # Test 10s
            time.sleep(1)
            print("{:2d}".format(i), end=" ", flush=True)
        camera.exposure_mode = 'off'

        print("")
        print("________________________________________")
        myprint("camera.iso", camera.iso)
        myprint("camera.framerate", camera.framerate)
        myprint("camera.framerate_range", camera.framerate_range)
        myprint("camera.shutter_speed", camera.shutter_speed)
        myprint("camera.exposure_speed", camera.exposure_speed)
        myprint("camera.exposure_mode", camera.exposure_mode)
        myprint("camera.digital_gain", camera.digital_gain)
        myprint("camera.analog_gain", camera.analog_gain)
        print("________________________________________")
        
        if camera.analog_gain == 0 or camera.digital_gain == 0 or camera.exposure_speed == 0:
            print("Digital and/or analog gain is 0! Pixels will be black.")
            print("Try increasing the camera warm up time.")
            exit_script()
        
        # Take Picture
        if not background:
            # First image as background image
            start = time.time()
            camera.capture(output, 'jpeg', bayer=True)
            stop = time.time()
            pv_additional_info(pv_additionals, pv_list)
            print("Background picture was taken within {:.3g}s!".format(stop-start))
            res_time.append(stop-start)
            
            # Background image processing
            pic_name = "background"
            imgarray = output.array
            now = datetime.datetime.now()
            plot_pic(pic_path, pic_name, imgarray, now)
            write_camtab(pic_path, pic_name, camera, camlist)
            save_to_npz(pic_path, pic_name, imgarray, now, camera, camlist, 0, 0)
            print("________________________________________")

            # Start taking pictures            
            for pic_id in range(num_of_pics):
                

                print("Camera is ready. Waiting for trigger signal...", flush=True)
                print("Trigger ready")
                
                try:
                    timeout = 300000
                    trigger = GPIO.wait_for_edge(p_trig, GPIO.RISING, timeout = timeout)  
                    
                    if trigger:
                        print("Triggered! Don't change any pv until all is saved.")
                        start = time.time()
                        camera.capture(output, 'jpeg', bayer=True)
                        stop = time.time()
                        pv_additional_info(pv_additionals, pv_list)
                        if quad_i_get == None or quad_i_set == None:
                            i_get, i_set = 0, 0
                            pic_name = "{}_{:03d}".format(pic_name_save, pic_id)                
                            print("pic_id = {}".format(pic_id))
                        else:
                            i_get = round(quad_i_get.get(),6)
                            i_set = round(quad_i_set.get(),6)
                            pic_name = "qd{}s_{:=+05d}mA".format(quad_no, int(i_set*1e3))                
                            print("pic_id {}: quad_no = {}, i_set = {} A, i_get = {} A".format(pic_id, quad_no, i_set, i_get))

                        print("Picture {:02d} was taken within {:.3f}s".format(pic_id, stop-start))
                        res_time.append(stop-start)
                        
                        # Image processing
                        imgarray = output.array
                        now = datetime.datetime.now()

                        ## Plot
                        plot_pic(pic_path, pic_name, imgarray, now)
                        write_camtab(pic_path, pic_name, camera, camlist)
                        save_to_npz(pic_path, pic_name, imgarray, now, camera, camlist, i_set, i_get, pv_additionals)


                        print("Pictures taken successfully, saving to: {}".format(pic_name), flush=True)
                        print("________________________________________")
                        
                    else:
                        print("Timeout: no trigger detected withing {}ms.".format(timeout))
                        print("________________________________________")
                        break
                        
                except KeyboardInterrupt:
                    exit_script()
                
            print("<time to take picture> = ({:.3f} +/- {:.3f})s".format(np.mean(res_time), np.std(res_time)))
                    
        # Background picture
        else:
            pic_name = "background"
            print("Taking background picture!")
            camera.capture(output, 'jpeg', bayer=True)
            imgarray = output.array
            now = datetime.datetime.now()

            plot_pic(pic_path, pic_name, imgarray, now)
            write_camtab(pic_path, pic_name, camera, camlist)
            save_to_npz(pic_path, pic_name, imgarray, now, camera, camlist, 0, 0)

            print("Pictures taken successfully, saving to: {}".format(pic_name), flush=True)
            

print("Stopping picamera", flush=True)


# ===== Start Webserver =====
print("Starting Webserver", flush=True)
subprocess.call(['/home/pi/RPi_Cam_Web_Interface/start.sh'])

GPIO.cleanup()
print("Done")
