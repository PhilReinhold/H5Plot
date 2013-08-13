H5Plot
======

Dependencies
------------

* PyQt4
* numpy
* [objectsharer](http://github.com/heeres/objectsharer) :: proxying of python objects across the network
* [dataserver](http://github.com/heeres/dataserver) :: shareable [h5py](http://www.h5py.org) files
* [pyqtgraph](http://www.pyqtgraph.org) :: Native Python Qt plotting library

Usage
-----
Run dataserver

    python dataserver/dataserver.py

or

    from dataserver import run_dataserver
    run_dataserver()

Run gui

    python H5Plot/window.py

 or

     from H5Plot import run_plotwindow
     run_plotwindow()

Send Data to DataServer

    from dataserver import get_file
    f = get_file('test.h5')
    f['dataset'] = [1,3,2,4]

If you don't want to create new files every time you run, consider the
timestamp feature, which will create a new group inside the file, and return that instead

  f = get_file('test.h5', timestamp_group=True)
  f['dataset'] = [1,3,2,4]

