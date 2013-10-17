from dataserver import get_file
from demo_helpers import generate_rank1_data

f = get_file('attr_test.h5').get_numbered_child()
f['lines'] = generate_rank1_data()
f['lines'].set_attrs(x0=1, xscale=.01, xlabel='Time', ylabel='Noise')
