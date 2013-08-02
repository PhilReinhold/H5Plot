import dataserver_helpers
import numpy as np

f = dataserver_helpers.dataserver_client().get_file('attr_test.h5')
f['lines'] = np.random.normal(size=100)
f['lines'].set_attrs(x0=1, xscale=.01, xlabel='Time', ylabel='Noise')
