import numpy as np

from matplotlib import pyplot as plt
from skimage import data, img_as_float, color, exposure
import skimage.restoration as rest

from opensfdi import show_phasemap
from opensfdi.fringes import FringeFactory
from opensfdi.unwrap import itoh, reliability

import matplotlib.pyplot as plt

image = FringeFactory.MakeSinusoidal(1, 3, -np.pi / 2, width=4, height=4)[0]
#image = color.rgb2gray(img_as_float(data.chelsea()))

vals = np.array([
    np.array([2.1, 0.5, 0.2, 0.1]),
    np.array([0.3, 1.0, 1.9, 0.3]),
    np.array([1.6, 0.9, 0.2, 0.3]),
    np.array([0.1, 0.4, 0.1, 2.0]),
])

image = exposure.rescale_intensity(image, out_range=(0, 2 * np.pi))
#show_phasemap(image)

# Create a phase-wrapped image in the interval [-pi, pi)
image_wrapped = np.angle(np.exp(1j * image))
#show_phasemap(image_wrapped)

# Perform phase unwrapping
image_unwrapped = itoh.unwrap_phase(image_wrapped)
#show_phasemap(image_unwrapped)

image_unwrapped_2 = reliability.unwrap_phase(image_wrapped)
show_phasemap(image_unwrapped_2)

# Perform phase unwrapping
#image_unwrapped_3 = rest.unwrap_phase(image_wrapped)
#show_phasemap(image_unwrapped_3)

fig, ax = plt.subplots(2, 2, sharex=True, sharey=True)
ax1, ax2, ax3, ax4 = ax.ravel()

fig.colorbar(ax1.imshow(image, cmap='gray', vmin=0, vmax=4 * np.pi), ax=ax1)
ax1.set_title('Original')

fig.colorbar(ax2.imshow(image_wrapped, cmap='gray', vmin=-np.pi, vmax=np.pi), ax=ax2)
ax2.set_title('Wrapped phase')

fig.colorbar(ax3.imshow(image_unwrapped, cmap='gray'), ax=ax3)
ax3.set_title('Simple phase unwrapping')

fig.colorbar(ax4.imshow(image_unwrapped_2, cmap='gray'), ax=ax4)
ax4.set_title('Scikit phase unwrapping')

plt.show()