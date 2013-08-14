import numpy as np
from scipy import ndimage
from dataserver import get_file

f = get_file('simple_test.h5', timestamp_group=True)
f['lines'] = ndimage.gaussian_filter(np.random.normal(size=500), (8,))
f['image'] = 100 * ndimage.gaussian_filter(np.random.normal(size=(100, 100)), (8, 8))

print 'Done'