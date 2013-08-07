from interface import plotwindow_client
win = plotwindow_client(serverport=55563)
plot = win.add_plot('some test plot')
plot.set_data([6,4,3,3.5,2])


