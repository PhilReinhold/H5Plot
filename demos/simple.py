import H5Plot
import numpy as np
import time

with H5Plot.RemoteFile('test_simple.h5') as f:
    f['lines'] = np.random.normal(size=500)
    f['image'] = np.random.normal(size=(100, 100))

print 'Done'