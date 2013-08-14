from dataserver import get_file
from demo_helpers import generate_rank1_data, generate_rank2_data

f = get_file('simple_test.h5', timestamp_group=True)
f['lines'] = generate_rank1_data()
f['image'] = generate_rank2_data()

print 'Done'