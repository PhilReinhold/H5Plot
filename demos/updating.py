import numpy as np
from dataserver import get_file
import time

f = get_file('updating_test.h5')
for _ in range(4):
    time.sleep(.1)
    f['line'] = np.random.normal(size=100)
    f['img'] = (np.random.normal(size=(100, 100)))

print 'Done'
