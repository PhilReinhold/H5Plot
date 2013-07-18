import H5Plot
import time
import numpy as np

N = 100
wait = .1
mintime = N * wait

with H5Plot.RemoteFile('stress_test.h5') as f:
    for chunk_size in [10, 100, 1000]:
        starttime = time.time()
        dset = f['size' + str(chunk_size)]
        for _ in range(N):
            dset.append_data(np.random.normal(size=chunk_size))
            time.sleep(wait)
        tottime = time.time() - starttime
        print chunk_size, ':', tottime, '/', mintime, '=', ('%.2f' % (tottime / mintime))
print 'Done'