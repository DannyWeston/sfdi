
import numpy as np
import cv2

import logging
import json
import os

from time import sleep, perf_counter
from datetime import datetime
from scipy.ndimage import gaussian_filter
from scipy.interpolate import griddata

from sfdi.utils import maths
from sfdi.video import Camera, PygameProjector
from sfdi.definitions import RESULTS_DIR, FRINGES_DIR

class Experiment:
    def __init__(self, camera=Camera(), projector=PygameProjector(1280, 720), debug=False):
        self.debug = debug  # Debug mode or not

        self.logger = logging.getLogger()

        self.camera = camera
        self.projector = projector 

    def run(self, fringe_paths, refr_index, mu_a, mu_sp, run_count):
        # TODO: Abstract this into image collection class
        # TODO: Abstract calculations into class

        self.logger.info(f'Starting experiment')
        timestamp = f'{datetime.now().strftime("%Y%m%d_%H%M%S")}'

        # Load the fringe patterns
        fringe_patterns = [self.load_fringe_pattern(fringe) for fringe in fringe_paths]

        # Iterate through the runs, storing the results where necessary
        successful = 0
        for i in range(1, run_count + 1):
            self.logger.info(f'Starting run {i}')

            # Load the images to be used (use already provided images if in debug)
            if self.debug: 
                imgs, ref_imgs = self.test_images()

            else: 
                ref_imgs = self.collect_images(fringe_patterns)
                #TODO: Introduce way to prompt user they have the object in place
                imgs = self.collect_images(fringe_patterns)

            # Calculate parameters
            calc_time = perf_counter()
            results = self.calculate(ref_imgs, imgs, refr_index, mu_a, mu_sp)
            calc_time = perf_counter() - calc_time

            if results is None: 
                # TODO: Write error message to console
                continue

            successful += 1
            
            self.logger.info(f'Calculation completed in {calc_time:.2f} seconds')
            
            self.save_results(results, f'{timestamp}_{i}.json')

            self.logger.info(f'Run {i} completed')

        self.logger.info(f'{successful}/{run_count} total runs successful)')

    def calculate(self, ref_imgs, imgs, refr_index, mu_a, mu_sp):
        f = [0, 0.2]

        # Calculate some constants

        R_eff = maths.ac_diffuse(refr_index)
        A = (1 - R_eff) / (2 * (1 + R_eff))
        mu_tr = mu_sp + mu_a
        ap = mu_sp / mu_tr

        std_dev = 3

        # Apply some gaussian filtering

        ref_imgs_ac = gaussian_filter(maths.AC(ref_imgs), std_dev)
        ref_imgs_dc = gaussian_filter(maths.DC(ref_imgs), std_dev)

        imgs_ac = gaussian_filter(maths.AC(imgs), std_dev)
        imgs_dc = gaussian_filter(maths.DC(imgs), std_dev)

        # Get AC/DC Reflectance values using diffusion approximation
        r_ac, r_dc = maths.diffusion_approximation(refr_index, mu_a, mu_sp, f[1])

        R_d_AC2 = (imgs_ac / ref_imgs_ac) * r_ac
        R_d_DC2 = (imgs_dc / ref_imgs_dc) * r_dc

        xi = []
        x, y = R_d_AC2.shape
        # Put the DC and AC diffuse reflectance values into an array
        for i in range(x):
            for j in range(y):
                freq = [R_d_DC2[i][j], R_d_AC2[i][j]]
                xi.append(freq)

        # Get an array of reflectance values and corresponding optical properties
        mu_a = np.arange(0, 0.5, 0.001) # We are setting the absorption coefficient range
        mu_sp = np.arange(0.1, 5, 0.01)

        n = 1.43 # Refractive index of tissue

        # THE DIFFUSION APPROXIMATION
        # Getting the diffuse reflectance AC values corresponding to specific absorption and reduced scattering coefficients
        Reflectance_AC = []
        Reflectance_DC = []
        op_mua = []
        op_sp = []
        for i in range(len(mu_a)):
            for j in range(len(mu_sp)):
                R_eff = 0.0636 * n + 0.668 + 0.710 / n - 1.44 / (n ** 2)
                A = (1 - R_eff) / (2 * (1 + R_eff))
                mu_tr = mu_a[i] + mu_sp[j]
                ap = mu_sp[j] / mu_tr

                g = lambda mu_effp: (3 * A * ap) / (((mu_effp / mu_tr) + 1) * ((mu_effp / mu_tr) + 3 * A)) 

                ac = maths.mu_eff(mu_a[i], mu_tr, f[1])
                dc = maths.mu_eff(mu_a[i], mu_tr, f[0])

                Reflectance_AC.append(g(ac))
                Reflectance_DC.append(g(dc))

                op_mua.append(mu_a[i])
                op_sp.append(mu_sp[j])

        # putting the DC and AC diffuse reflectance values generated from the Diffusion Approximation into an array    
        points = []
        for k in range(len(mu_a) * len(mu_sp)): 
            freq = [Reflectance_DC[k], Reflectance_AC[k]]
            points.append(freq)

        points_array = np.array(points)
        #putting the optical properties into two seperate arrays
        op_mua_array = np.array(op_mua)
        op_sp_array = np.array(op_sp)

        #using scipy.interpolate.griddata to perform cubic interpolation of diffuse reflectance values to match 
        #the generated diffuse reflectance values from image to calculated optical properties
        interp_method = 'cubic'
        coeff_abs = griddata(points_array, op_mua_array, xi, method=interp_method) #mua
        coeff_sct = griddata(points_array, op_sp_array, xi, method=interp_method) #musp

        abs_plot = np.reshape(coeff_abs, (R_d_AC2.shape[0], R_d_AC2.shape[1]))
        sct_plot = np.reshape(coeff_sct, (R_d_AC2.shape[0], R_d_AC2.shape[1]))

        absorption = np.nanmean(abs_plot)
        absorption_std = np.std(abs_plot)

        scattering = np.nanmean(sct_plot)
        scattering_std = np.std(sct_plot)


        self.logger.info(f'Absorption: {absorption}')
        self.logger.info(f'Deviation std: {absorption_std}')

        self.logger.info(f'Scattering: {scattering}')
        self.logger.info(f'Scattering std: {scattering_std}')

        return {
            "absorption" : absorption,
            "absorption_std_dev" : absorption_std,
            "scattering" : scattering,
            "scattering_std_dev" : scattering_std,
        }

    def save_results(self, results, name):
        with open(os.path.join(RESULTS_DIR, name), 'w') as outfile:
            json.dump(results, outfile, indent=4)
            self.logger.info(f'Results saved in {name}')

    def load_fringe_pattern(self, name):
        self.logger.info(name)
        img = cv2.imread(os.path.join(FRINGES_DIR, name))
        return img.astype(np.double)

    # Returns a list of n * 2 images (3 to use, 3 reference)
    def test_images(self):
        imgs = []
        ref_imgs = []

        img_paths = self.proj_imgs[:3]
        ref_img_paths = self.proj_imgs[3:]

        #TODO: Chekc if images correctly loaded
        for path in img_paths:
            img = cv2.imread(path, 1).astype(np.double)
            img = img[:, :, 2] # Only keep red channel in images
            imgs.append(img)

        for path in ref_img_paths:
            ref_img = cv2.imread(path, 1).astype(np.double)
            ref_img = ref_img[:, :, 2] # Only keep red channel in images
            ref_imgs.append(ref_img)

        return imgs, ref_imgs

    def collect_images(self, fringe_patterns, delay=3):
        imgs = []

        for i in range(len(fringe_patterns)):
            self.projector.display(img)
            sleep(delay)

            img = self.camera.capture()
            cv2.imwrite(f"{self.output_dir}/results/images/{i},jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            sleep(delay)

            imgs.append(img)

        return imgs
    
    def __del__(self):
        if self.camera: del self.camera

        if self.projector: del self.projector