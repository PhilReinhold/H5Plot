from dataserver import get_file
from demo_helpers import *

f = get_file('updating_test.h5', timestamp_group=True)
for _ in range(20):
    print "Enter to Step",
    raw_input()
    f['line'] = generate_rank1_data()
    f['img'] = generate_rank2_data()

print 'Done'
