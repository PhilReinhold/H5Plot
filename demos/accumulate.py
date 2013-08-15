import numpy as np
from dataserver import get_file
from demo_helpers import generate_rank1_data, generate_rank2_data

f = get_file('accumulating_test.h5', timestamp_group=True)

f.create_dataset('line', rank=1)
f.create_dataset('img', rank=2)

for x, trace in zip(generate_rank1_data(), generate_rank2_data()):
    #time.sleep(.1)
    print "Enter to step",
    raw_input()
    f['line'].append(np.random.normal())
    f['img'].append(np.random.normal(size=100))

print 'Done'
