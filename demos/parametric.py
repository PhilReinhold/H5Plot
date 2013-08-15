import numpy as np
from dataserver import get_file
from demo_helpers import generate_rank1_data

# TODO, make scatter

f = get_file('parametric_test.h5', timestamp_group=True)
f.create_dataset('random walk', rank=2)
#f.create_dataset('3d random walk', rank=2)
f['random walk'].set_attrs(parametric=True)
#f['3d random walk'].set_attrs(parametric=True)
pos_2d = np.zeros(2)
#pos_3d = np.zeros(3)

xs, ys, zs = (generate_rank1_data() for _ in range(3))
for x, y, z in zip(xs, ys, zs):
    raw_input("Enter to Step")
    pos_2d += (x, y)
#    pos_3d += (x, y, z)
    f['random walk'].append(pos_2d)
#    f['3d random walk'].append(pos_3d)

print 'Done'
