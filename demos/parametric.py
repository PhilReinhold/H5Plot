import numpy as np
from dataserver import get_file
#from H5Plot import plotwindow_client
import time

f = get_file('stress_test.h5', timestamp_group=True)
f.create_dataset('random walk', rank=2)
f['random walk'].set_attrs(parametric=True)
#win = plotwindow_client()
#win.config_plot('random scatter', scatter=True) # TODO
pos = np.array([0, 0], dtype=np.float64)
for _ in range(300):
    time.sleep(.1)
    f['random walk'].append(pos)
    #f['random scatter'].append(pos)
    pos += np.random.normal(size=2)

print 'Done'
