import H5Plot
import numpy as np
import time

pos = np.array([0, 0], dtype=np.float64)
with H5Plot.RemoteFile('parametric_test.h5') as f:
    for _ in range(300):
        time.sleep(.1)
        f['random_walk'].append_data(pos, parametric=True)
        pos += np.random.normal(size=2)

print 'Done'
