import numpy as np
from scipy import ndimage
from dataserver import get_file

f = get_file('updating_test.h5', timestamp_group=True)
for _ in range(20):
    print "Enter to Step",
    raw_input()
    f['line'] = ndimage.gaussian_filter(np.random.normal(size=500), (8,))
    f['img'] = 100 * ndimage.gaussian_filter(np.random.normal(size=(100, 100)), (8, 8))

print 'Done'
