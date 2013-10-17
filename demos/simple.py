from dataserver import get_file
from demo_helpers import generate_rank1_data, generate_rank2_data

f = get_file('simple_test.h5')
f = f.get_group('simple group')
f = f.get_numbered_child()
f['lines'] = generate_rank1_data()
f['image'] = generate_rank2_data()

print 'Done'