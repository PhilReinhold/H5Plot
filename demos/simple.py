import numpy as np
from dataserver import get_file

f = get_file('simple_test.h5', timestamp_group=True)
f['lines'] = np.random.normal(size=500)
f['image'] = np.random.normal(size=(100, 100))

print 'Done'