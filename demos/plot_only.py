from H5Plot import plotwindow_client
from demo_helpers import generate_rank1_data

win = plotwindow_client(serverport=55563)
plot = win.add_plot('some test plot')
plot.set_data(generate_rank1_data())
