#!/usr/local/bin/python3.6
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
import sys

from fractions import Fraction

os.environ['PYEPICS_LIBCA'] = "/home/epics/base/lib/linux-arm/libca.so"

# Camera attributes to save
camlist = ['sensor_mode', 'iso', 'shutter_speed', 'exposure_mode', 'framerate', 'digital_gain', 'analog_gain', 'revision', 'exposure_speed']

pv_list = ['steam:laser:setamp_get', 'steam:laser:dc_get', 'steam:laser:pl_get', 'steam:powme1:pow_get', ]

try:
    import RPi.GPIO as GPIO
except:
    pass

# Methods
def make_dir(type, path_time, pic_dir_time):
    if type == 'single':
        pic_path = "/home/pi/python/quadscan/{}_pics/{}".format(type, path_time)
    else:
        pic_path = "/home/pi/python/quadscan/{}_pics/{}/{}".format(type, path_time, pic_dir_time)
        
    if not os.path.isdir(pic_path):
        print("Directory does not exist yet, making dir {}".format(pic_path))
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
    return pic_path


def plot_pic(path, name, imgarray, start_now):
    """Sum raw imgarray = img; plot img with colorbar and save to outfile."""
    fig, ax = plt.subplots(figsize=(11,8))
    img = sum(imgarray[:, :, i] for i in range(3))
    ax_img = ax.imshow(img, aspect='auto', cmap=plt.get_cmap('jet'))
    cb = plt.colorbar(ax_img, ax=ax)
    fig.text(0.01,0.01, start_now.strftime("%d.%m.%y %H:%M:%S"))
    out = "{}/{}".format(path, name)
    plt.suptitle(out)
    plt.savefig(out + ".png")
    plt.close('all')


def myprint(idx_name, idx_value):
    """Simple print variable name and its value."""
    print("{} = {}".format(idx_name, idx_value))


def roi_img_center(array, roi_fy = 750, roi_fx = 750):
    """Return equally spaced distance of roi_f around center."""
    
    def roi (coord, roi_f = 750, p=0):
        """Returns given coordinate +/- roi_f"""
        return int(round(coord+(-1)**p*roi_f))
        
    try:
        yc, xc = [coord /2 for coord in array.shape[:2]]
        imgarray_roi = array[roi(yc, roi_fy, 1):roi(yc, roi_fy), roi(xc,roi_fx, 1):roi(xc, roi_fx) , :]
        return imgarray_roi
        
    except:
        print("Error calculating roi. Using full view.")
        return array


def roi_img(array, left, lower, right, upper):
    """Return equally spaced distance of roi_f around center."""
    if not left >= right or not lower <= upper:
        try:
            imgarray_roi = array[upper:lower, left:right, :]
            return imgarray_roi
        
        except:
            print("Error calculating roi. Using full view.")
            return array
            
    else:
        print("ROI error: left >= right or lower >= upper. Using full view instead.")
        return array

def write_camtab(path, name, camera, camlist):
    """unless pic_name is foo; open a file named cam_tab and write camlist to it."""
    with open("{}/cam_tab.txt".format(path), 'a') as f:
        try:
            f.write("{}\t".format(name))
            for k in camlist:
                attr = getattr(camera, k)
                f.write("{}\t".format(attr))
        finally:
            f.write("\n")


def exit_script(gpio = False):
    print("Aborting script.")
    if gpio: GPIO.cleanup()
    sys.exit(0)


def save_to_npz(path, name, imgarray, timestamp, cam, camlist, i_set = None, i_get = None, pv_additionals = None):
    """Grep camera attributes and save pic,timestamp and specs to output"""
    out = "{}/{}.npz".format(path, name)
    picam_specs = {}
    for k in camlist:
        attr = str(getattr(cam, k))
        picam_specs[k] = attr
        
    if not i_set == None:
        curr_set = round(i_set,6)
    else:
        curr_set = None
    res_dict = {'curr_set': curr_set, 'curr_get': i_get, 
                'img': imgarray, 'timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S")}
    if pv_additionals != None: res_dict = {**res_dict, **pv_additionals}
    res_dict['picamera']=picam_specs
    res_dict = {name : res_dict}
    
    if os.path.isfile(out):
        print("File already exists: {}".format(out))
        override = input("Do you want to override it? [Y,y]")
        if not any(override == yes for yes in ['Y','y']):
            print("Picture not saved.")
            return None
    print("Saving...", end="")
    np.savez_compressed(out, **res_dict)
    print("Done")


def pv_additional_info(pv_additionals, pv_list):
    """Get values and units from pvs in pv_list and put them in dictionary pv_additionals"""
    for pv in pv_list:
        pv_value = epics.caget(pv)
        pv_unit = epics.caget(pv + ".EGU")
        pv_additionals[pv] = [pv_value, pv_unit]

