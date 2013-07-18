import H5Plot
import numpy as np
import time

with H5Plot.RemoteFile('updating_test.h5') as f:
    for _ in range(200):
        time.sleep(.03)
        f['accumulating line'].append_data(np.random.normal())
        f['refreshing line'] = np.random.normal(size=100)
        f['accumulating img'].append_data(np.random.normal(size=100))
        f['refreshing img'] = (np.random.normal(size=(100, 100)))

print 'Done'
