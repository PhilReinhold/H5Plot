import numpy as np
from dataserver_helpers import dataserver_client

c = dataserver_client()
f = c.get_file('simple_test.h5')
f['lines'] = np.random.normal(size=500)
#f['image'] = np.random.normal(size=(100, 100))

print 'Done'