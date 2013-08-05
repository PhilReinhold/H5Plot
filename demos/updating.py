import numpy as np
from dataserver import get_file
import time

f = get_file('updating_test.h5')
for _ in range(10):
    time.sleep(.1)
    #f['accumulating line'].append_data(np.random.normal())
    f['refreshing line'] = np.random.normal(size=100)
    #f['accumulating img'].append_data(np.random.normal(size=100))
    f['refreshing img'] = (np.random.normal(size=(100, 100)))

print 'Done'
