from skimage.restoration import unwrap_phase

import numpy as np
import cv2
from matplotlib import pyplot as plt    
from mpl_toolkits.mplot3d import Axes3D

import logging

import argparse

parser = argparse.ArgumentParser()

parser.add_argument('--debug', action='store_true')

args, unknown = parser.parse_known_args()

args = vars(args)

DEBUG = args["debug"]

logging.basicConfig(format = "[%(levelname)s] %(message)s")
logging.getLogger("sfdi").setLevel(logging.DEBUG if DEBUG else logging.INFO)

def show_surface(data):
    hf = plt.figure()
    ha = hf.add_subplot(111, projection='3d')

    X, Y = np.meshgrid(range(len(data[0])), range(len(data)))  # `plot_surface` expects `x` and `y` data to be 2D
    ha.plot_surface(X, Y, data)

    plt.show()
        
def display_image(img, grey=False, title='', vmin=0, vmax=255):
    if grey:
        cmap='gray'
    else:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        cmap='jet'

    plt.imshow(img, cmap=cmap, vmin=vmin, vmax=vmax)
    plt.title(title)
    plt.show()

def centre_crop_img(img, x1, y1, x2=None, y2=None):
    x3 = x2 if x2 else -x1
    y3 = y2 if y2 else -y1
    return img[x1 : x3, y1 : y3]

def rgb2grey(img):
    r, g, b = img[:,:,0], img[:,:,1], img[:,:,2]
    return 0.2989 * r + 0.5870 * g + 0.1140 * b

def unwrapped_phase(phi_imgs):
    return unwrap_phase(phi_imgs)

def wrapped_phase(imgs):
    p = q = 0

    for i, img in enumerate(imgs):
        phase = (2.0  * np.pi * i) / len(imgs)
        p += img * np.sin(phase)
        q += img * np.cos(phase)

    return -np.arctan2(p, q)

def ac_imgs(imgs: list):
    total = 0
    for img in imgs:
        total += img
        
    return (1.0 / len(imgs)) * total

def dc_imgs(imgs: list):
    N = len(imgs)
    
    p = 0
    q = 0
    
    for i, img in enumerate(imgs):
        phase = (2.0 * np.pi * i) / N 
        
        p += img * np.sin(phase)
        q += img * np.cos(phase)
        
    return (2.0 / N) * np.sqrt((p * p) + (q * q))