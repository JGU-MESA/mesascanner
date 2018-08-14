import os
import sys
import python_method_analysis as pma


if len(sys.argv) != 4:
    print("Usage: python {} <quadscan_pics|oneshot_pics> <measure_date, e.g. 180810> <timestamp, e.g. 0904>")
    sys.exit()
    
print("===== Picture measurement main analysis script =====")
print("path pattern: ...\\<quadscan_pics|oneshot_pics>\\<measure_date>\\<measure_date>_<measure_time>\\...")
print("Before starting, check if defaults are correct:")
print("- px2mm =  {} # Convert pixel to mm according to last scale picture".format(pma.px2mm))
print("- sub_roi =  {} # Region of interest for fitting".format(pma.sub_roi))
print("- s = {} m # effective length".format(pma.s))
print("- l = {} # Drift distance in m".format(pma.l))
print("- dBdsi = {} T/(Am)".format(pma.dBdsi))
print("- ep = {} m/(Vs)".format(pma.ep))
#================================================================================
# Confirmation
pma.printeq()
answer = input("Are these parameters still correct?[Yy]")
if not any(answer == itm for itm in ['Y', 'y']):
    print("Then change! They are located here: {}".format(pma.__file__))
    sys.exit()

#================================================================================
os.system("python P1_python_picture_get_sigma_2d_gaussian_fit.py " + sys.argv[1] + " " + sys.argv[2] + " " + sys.argv[3])
pma.printeq()
os.system("python P2_python_picture_emittance.py " + sys.argv[1] + " " + sys.argv[2] + " " + sys.argv[3])
pma.printeq()