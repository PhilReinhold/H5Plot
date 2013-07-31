import numpy as np
from dataserver import get_file
from H5Plot import get_window
import time

f = get_file('stress_test.h5')
win = get_window()
win.config_plot('random scatter', scatter=True)
pos = np.array([0, 0], dtype=np.float64)
for _ in range(300):
    time.sleep(.1)
    f['random walk'].append(pos)
    f['random scatter'].append(pos)
    pos += np.random.normal(size=2)

print 'Done'
