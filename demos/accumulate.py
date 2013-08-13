import numpy as np
from dataserver import get_file
import time
from H5Plot.helpers import get_available_filename

filename = get_available_filename(r'C:\_Data\accumulating_test')
f = get_file(filename)

f.create_dataset('line', rank=1)
f.create_dataset('img', rank=2)

for _ in range(10):
    time.sleep(.1)
    f['line'].append(np.random.normal())
    f['img'].append(np.random.normal(size=100))

print 'Done'
