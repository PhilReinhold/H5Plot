from H5Plot import plotwindow_client
import numpy as np

win = plotwindow_client(serverport=55563)
plot = win.add_plot('some test plot')
plot.set_data(np.random.normal(size=10))
