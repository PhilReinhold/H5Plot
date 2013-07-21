import H5Plot
import numpy as np
import h5py
import os

filename = 'saving_test.h5'
with H5Plot.RemoteFile(filename) as f:
    test_data = np.random.normal(size=100)
    f['data'] = test_data
    f.remove_item() # Relinquish control of the file handle so we can test it

assert os.path.exists(filename)
f = h5py.File(filename)
assert all(np.equal(f['data'], test_data))
f.close()
os.remove(filename)

print 'Done'
