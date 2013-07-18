from math import sqrt
from numpy import zeros, ones, dot, array
from scipy.linalg import expm


def cube(n):
    if n is 0:
        return [()]
    else:
        sub_cube = cube(n - 1)
        return [(-1,) + s for s in sub_cube] + [(1,) + s for s in sub_cube]


def rotation_generator(axis):
    la = len(axis)
    n = int((1 + sqrt(8 * la + 1)) / 2)
    if n * (n - 1) / 2 != len(axis):
        raise ValueError('Invalid axis, length must be a triangle number ' +
                         'corresponding to the upper half of the rotation generator')
    rgen = zeros((n, n))
    axis_ind = 0
    for i in range(1, n):
        for j in range(1, i):
            rgen[i, j] = axis[axis_ind]
            rgen[j, i] = -axis[axis_ind]
            axis_ind += 1
    return rgen


def rotation_matrix(axis, timestep):
    return expm(rotation_generator(axis) * timestep)


def test_cube():
    assert set(cube(1)) == set([(-1,), (1,)])
    assert set(cube(2)) == set([(-1, -1), (-1, 1), (1, -1), (1, 1)])


def project(cube):
    return (array([p[0] for p in cube]), array([p[1] for p in cube]))


if __name__ == "__main__":
    from H5Plot import RemoteFile
    from time import sleep

    test_cube()
    f = RemoteFile('cube_test.h5')
    cube_dim = None
    axis = ones(8)
    f.attrs['n'] = 3
    f.attrs['timestep'] = .01
    while True:
        if f.attrs['n'] != cube_dim:
            cube_dim = f.attrs['n']
            local_cube = cube(cube_dim)
            axis = ones(cube_dim * (cube_dim - 1) / 2)
            #print axis.shape, rotation_matrix(axis, f.attrs['timestep']).shape, local_cube.shape
        local_cube = [dot(rotation_matrix(axis, f.attrs['timestep']), point) for point in local_cube]
        #print project(local_cube)
        f['cube'].set_data(project(local_cube), pen=None, symbolPen=None, symbol='o')
        sleep(1)

