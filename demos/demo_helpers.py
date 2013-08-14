import numpy as np
from scipy import ndimage

def generate_rank1_data():
    return ndimage.gaussian_filter(np.random.normal(size=100), (8,))

def generate_rank2_data():
    return 100 * ndimage.gaussian_filter(np.random.normal(size=(100, 100)), (8, 8))
