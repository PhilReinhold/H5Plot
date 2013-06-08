from distutils.core import setup
import py2exe
import os
import zmq

os.environ["PATH"] = \
    os.environ["PATH"] + \
    os.path.pathsep + os.path.split(zmq.__file__)[0]

windows = [{'script': 'main.py', 'icon_resources': [(0, 'plot.ico')]}]
#setup(console=['launcher.py'], options={'py2exe':{'includes':['sip']}})
setup(name='pachyderm',
      version='0.1',
      install_requires=['numpy', 'Pyro4', 'h5py'],
      windows=windows,
      options={'py2exe':
                   {'includes':
                        ['sip', 'zmq.utils',
                         'zmq.utils.jsonapi',
                         'zmq.utils.strtypes',
                         'scipy.sparse.csgraph._validation',
                         'h5py.defs',
                         'h5py.utils']}})