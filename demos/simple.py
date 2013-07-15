import H5Plot
import numpy as np

print "F"
with H5Plot.RemoteFile('test.h5') as f:
    print "E"
    f['lines'] = np.random.normal(size=500)
    f['image'] = np.random.normal(size=(100, 100))

print 'Done'