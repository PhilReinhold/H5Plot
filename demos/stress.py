import H5Plot
import time
import numpy as np

N = 1000
wait = .01
mintime = N * wait

with H5Plot.RemoteFile('stress_test.h5') as f:
    starttime = time.time()
    for chunk_size in [100, 1000, 10000]:
        dset = f['size' + str(chunk_size)]
        for _ in range(N):
            dset.append_data(np.random.normal(size=chunk_size))
            time.sleep(wait)
    tottime = time.time() - starttime
    print chunk_size, ':', tottime, '/', mintime, '=', ('%.2f' % (tottime / mintime))

