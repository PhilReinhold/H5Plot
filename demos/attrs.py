from dataserver import get_file
import numpy as np

f = get_file('attr_test.h5', timestamp_group=True)
f['lines'] = np.random.normal(size=100)
f['lines'].set_attrs(x0=1, xscale=.01, xlabel='Time', ylabel='Noise')
