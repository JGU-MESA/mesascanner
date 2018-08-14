import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import scipy.optimize as opt
import os
import sys

# Regex
renum = r'[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'  # regex for arbitrary number
ibdpattern = 'Ibd = \({d} \+/- {d}\)\w\s\({d}%\)'.format(d=renum)

# Miscellanous
s = 0.04921     # effektive Länge in m
l = {20: {1: 0.3979, 2: 0.2659, 3: 0.1339}, 50: {1: 0.3575, 2: 0.2255, 3: 0.0935}}
dBdsi = {1: 0.474, 2: 0.472, 3: 0.472}  # melba_020:trip_q<1|2|3>
ep = 895.394   # e/p in m/(Vs)

# Picture analysis
px2mm = 20/(2480 - 1060)
## Sub region of interest (top, bottom, left, right) with view from imshow -> y-axis inverted
sub_roi = [350, 1200, 800, 1400]

np.set_printoptions(precision=3)

def printeq():
    print("============================================================")


def load_image(pic_path, pic_name):
    """ Load image by path and name, assuming its saved in *.npz"""
    if not pic_name.endswith(".npz"):
        print("Picture must be saved in .npz-File with its name as key and 'img' as subkey.")
        return None
    try:
        with np.load(pic_path + pic_name) as file:
            image = sum([file[pic_name[:-4]].all()['img'][:,:,i] for i in range(3)])
            timestamp = file[pic_name[:-4]].all()['timestamp']
            curr_get = file[pic_name[:-4]].all()['curr_get']
    except:
        print("Error: Could not load image")
        return None
    else:
        return image, timestamp, curr_get


def subtract_background(image, bckg_img):
    sx, sy = image.shape[1], image.shape[0]
    image_wob = np.empty((sy,sx), dtype=image.dtype)
    for row in range(sy):
        for col in range(sx):
            if image[row, col] <= bckg_img[row, col]: image_wob[row, col] = 0
            else : image_wob[row, col] = image[row, col] - bckg_img[row, col]
    return image_wob


def check_theta(theta_rad):
    pi = np.pi
    if theta_rad < 0:
       theta_rad_2pi = theta_rad % -(2*pi)  # theta = theta modulo 360deg
    else:
       theta_rad_2pi = theta_rad % (2*pi)  # theta = theta modulo 360deg    
    return theta_rad_2pi


def check_sigma(sigma_x, sigma_y):
    if sigma_y > sigma_x:
        sigma_x, sigma_y = abs(sigma_y), abs(sigma_x)
    else:
        sigma_x, sigma_y = abs(sigma_x), abs(sigma_y)
    return sigma_x, sigma_y

def curr2k(curr_get, quad_no):
    return ep * dBdsi[quad_no] * curr_get

def gaussian(x, a, mu, sigma, offset, p=1):
    return a * np.exp(-((x - mu) ** 2 / (2 * sigma ** 2)) ** p) + offset

def two_dim_gaussian(xy_mesh, amplitude, xo, yo, sigma_x, sigma_y, offset, theta):
    """2dim gaussian distribution. DO NOT CHANGE THE ORDER OF PARAMETER"""
    #DEBUG
    theta = check_theta(theta)
    sigma_x, sigma_y = check_sigma(sigma_x, sigma_y)
    xo, yo = float(xo), float(yo)
    x, y = xy_mesh[0], xy_mesh[1]
    a = (np.cos(theta) ** 2) / (2 * sigma_x ** 2) + (np.sin(theta) ** 2) / (2 * sigma_y ** 2)
    b = -(np.sin(2 * theta)) / (4 * sigma_x ** 2) + (np.sin(2 * theta)) / (4 * sigma_y ** 2)
    c = (np.sin(theta) ** 2) / (2 * sigma_x ** 2) + (np.cos(theta) ** 2) / (2 * sigma_y ** 2)
    res = offset + amplitude * np.exp(- (a * ((x - xo) ** 2) + 2 * b * (x - xo) * (y - yo) + c * ((y - yo) ** 2)))
    #DEBUG print("Fitting with: amp = {:.2f}, xo = {:.2f} px, yo = {:.2f} px, sigma_x = {:.2f} px, sigma_y = {:.2f} px, offset = {:.2f} px, theta = {:.2f} deg".format(amplitude, xo, yo, sigma_x, sigma_y, offset, np.rad2deg(theta)))
    return res.ravel()


def two_dim_gaussian_fit(img, name = "image", theta_rad=0.0, verbose=False):
    """"Fit 2d gaussian into picture and return its results. Pictures background should be subtracted before."""
    two_dim_gaussian_prams = two_dim_gaussian.__code__.co_varnames[1:two_dim_gaussian.__code__.co_argcount]

    
    # ========== Methods ==========
    def find_start_parameter_wo_theta(image):
        """This function should find the start parameter for a 2D_gaussian fit
            Parameters: amplitude, xo, yo, sigma_x, sigma_y, offset
            Theta must be rotated manually during the try-fit process"""
        if image.ndim < 2 or image.size == 0 :
            print("Error: Wrong image dimension: {}; or image size is zero".format(image.ndim))
            print("Abort finding start parameters")
            return None

        try:
            # image size: x = cols, y = rows
            sz_x, sz_y = image.shape[1], image.shape[0]

            # Maximum as amplitude
            amplitude, offset = np.max(img), np.min(img)

            # Location of 2D maximum as xo, yo
            amp_xo, amp_yo = np.array(np.unravel_index(np.argmax(image), image.shape))[::-1]

            # Standard deviation from maximum location
            sigma_x, sigma_y = map(lambda x: np.round(x * (1 - 0.69)), [amp_xo, amp_yo])

            # Gather start fit parameter for returning
            res = [amplitude, amp_xo, amp_yo, sigma_x, sigma_y, offset]

        except:
            print("Warning: Finding suitable start parameters failed!")
            res = None

        return res

        
    def abort_script():
        print("Error: Leaving script for picture '{}'".format(name))
        sys.exit()


    # ========== Calculations ==========
    print("Start calculating 2d gaussian fit for picture '{}'".format(name))
    sx, sy = img.shape[1], img.shape[0]
    print("Image size in pixels: {}".format(img.shape))

    # Start fit  amplitude, xo, yo, sigma_x, sigma_y, offset, theta
    start_param = find_start_parameter_wo_theta(img)
    if start_param is not None:
        print("Start fit parameter found: {}".format(start_param))
    else:
        print("Error: No start fit parameter found, aborting.")
        abort_script()

    # Creating mesh grid based on image size
    x, y = np.linspace(0, sx, sx), np.linspace(0, sy, sy)
    mesh_xy = np.meshgrid(x, y)
    
    # Add current theta to start fit parameter list
    fit_param = [*start_param, theta_rad]
    
    print("Try fit starting with theta = {} deg".format(np.rad2deg(theta_rad)))
    try:
        img_popt, img_pcov = opt.curve_fit(two_dim_gaussian, mesh_xy, img.ravel(), p0=fit_param)
        
    except ValueError:
        print("Error while fitting data: ValueError")
        abort_script()

    except RuntimeError:
        print("RuntimeError")
        return None

    except opt.OptimizeWarning:
        print("Warning: Covariance of the parameters can not be estimated")
        print("Warning: Maybe the start sigmas need to be changed")
        #break

    else:  # If try-statement is successful
        print("Fit successfull, starting post processing.")
        img_popt[-1] = check_theta(img_popt[-1])
        img_popt[3], img_popt[4] = check_sigma(img_popt[3], img_popt[4])
        
        # Plot resulting fit
        img_fit = two_dim_gaussian(mesh_xy, *img_popt)


        # Return results
        fit_zip = zip(img_popt, np.diagonal(img_pcov))
        fit_result_parameter_dict = dict(zip(two_dim_gaussian_prams, fit_zip))
        return {'img': img, 'img_fit': img_fit.reshape(sy, sx), 'fit_result_parameter_dict' : fit_result_parameter_dict, 'mesh_xy': mesh_xy, 'img_popt': img_popt, 'img_pcov': img_pcov}
    
    
def plot_image_and_fit(title, image, image_fit, 
                                    path = "last_img_fit.png", time = None, curr_get = None,
                                    sigmax = None, sigmax_err = None, sigmay = None, sigmay_err = None, unit = 'px'):
    """Save image and its fit to file"""
    if np.max(image_fit) > np.max(image): 
        max = np.max(image_fit)
    else:
        max = np.max(image)
    fig, axes = plt.subplots(figsize=(11,8), nrows=2, ncols=1, sharex=True)
    fig.suptitle(title, fontsize=16)
    im1 = axes[0].imshow(image, aspect='auto', cmap=plt.get_cmap('jet'), vmin = 0, vmax = max)
    im2 = axes[1].imshow(image_fit, aspect='auto', cmap=plt.get_cmap('jet'), vmin = 0, vmax = max)
    
    cax,kw = mpl.colorbar.make_axes([ax for ax in axes.flat])
    plt.colorbar(im1, cax=cax, **kw)
    
    curr_text = "I_quad = {} A".format(curr_get)
    res_textx = "sigma_x =  ({:.5f} +/- {:.5f}) {}".format(sigmax, sigmax_err, unit)
    res_texty = "sigma_y  = ({:.5f} +/- {:.5f}) {}".format(sigmay, sigmay_err, unit)
    fig.text(0.01,0.01, "{}, {}\n {} \n {}".format(time, curr_text, res_textx, res_texty))
    plt.savefig(path)
    plt.close('all')

def read_beamtimefile(file, measure_time):
    try:
        beamtimefile = np.genfromtxt(file, delimiter='\t', usecols=(1,7,8), dtype=[('beamtime','U4'),('amp',int),('ibd','|U50')])
    except:
        print("Could not read beamtimefile {}".format(file))
        return None, None
    else:
        ibd = beamtimefile['ibd'][beamtimefile['beamtime'] == measure_time][0]
        amp = beamtimefile['amp'][beamtimefile['beamtime'] == measure_time][0]
        return ibd, amp


def roi_img(array,  top, bottom, left, right):
    """Return equally spaced distance of roi_f around center."""
    if left < right and top < bottom:
        try:
            imgarray_roi = array[top:bottom, left:right]  
            return imgarray_roi
        
        except:
            print("Error calculating roi. Using full view.")
            return array
            
    else:
        print("ROI error: left >= right or top >= bottom. Using full view instead.")
        return array


def save_result(id, res, curr_get, path = "last_img_fit.npz" ):
    d = {}
    try:
        for itm in ['img_popt', 'img_pcov']:
            d[itm] = res[itm]
        d['curr_get'] = curr_get
        res = {id : d}
    except:
        print("Could not save result for {}".format(id))
        return None
    else:
        np.savez_compressed(path, **res)


def find_headers(file):
    """ Search file for header lines, which start with # """
    headers = []
    with open(file, 'r') as f:
        for line in f:
            if line[0] == '#':
                if line[-1] == '\n':
                    headers.append(line[1:-1].strip())
                else:
                    headers.append(line[1:].strip())
    return headers


def make_dir(path):
    if not os.path.isdir(path):
        print("Output directory does not exist yet, making dir {}".format(path))
        try:
            os.system("mkdir {}".format(path))
        except:
            print("Could not make directory, aborting")
            sys.exit(0)
    else:
        print("Output directory already exists")
        print("Results will be saved in directory {}".format(path))


def write_subdf_tofile(df, path):
    df.to_csv(path)