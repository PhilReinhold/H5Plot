import H5Plot
import numpy as np

with H5Plot.RemoteFile('axes_test') as f:
    f['lines'].set_data(np.random.normal(size=100), x0=1, xscale=.01,
                        xlabel='Time', ylabel='Gaussian Noise')
    pts = np.linspace(0, 10, 100)
    xpts, ypts = np.meshgrid(pts, pts)
    f['image'].set_data(10*np.sin(2*xpts + ypts) + np.random.normal(size=(100, 100)),
                        x0=1, xscale=.01, y0=1, yscale=.01,
                        xlabel='Time', ylabel='Space', zlabel='Noisy Sinusoid')
    f['image'][10,:] = np.zeros(100)
    f['image'][:,10] = np.zeros(100)
