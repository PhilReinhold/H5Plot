import numpy as np
from dataserver import get_file
import time

f = get_file('accumulating_test.h5')
reset = f.get_group('reset')
continuing = f.get_group('continuing')

 # force deletes existing dataset
reset.get_dataset('line', rank=1, force=True)
reset.get_dataset('img', rank=2, force=True)

 # allow_existing suppresses the error, and leaves the existing dataset untouched
continuing.get_dataset('line', rank=1, allow_existing=True)
continuing.get_dataset('img', rank=2, allow_existing=True)

for _ in range(4):
    time.sleep(.1)
    reset['line'].append(np.random.normal())
    reset['img'].append(np.random.normal(size=100))
    continuing['line'].append(np.random.normal())
    continuing['img'].append(np.random.normal(size=100))

print 'Done'
