import numpy as np
from dataserver import get_file
import time

f = get_file('accumulating_test.h5', timestamp_group=True)

f.create_dataset('line', rank=1)
f.create_dataset('img', rank=2)

for _ in range(10):
    time.sleep(.1)
    f['line'].append(np.random.normal())
    f['img'].append(np.random.normal(size=100))

print 'Done'
