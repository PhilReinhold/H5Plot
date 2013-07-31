import time
import sys

import cStringIO
import traceback

# Module imports for py2exe's benefit
import h5py._errors
import h5py._proxy
import h5py._objects
import h5py._conv

from PyQt4 import Qt
from window import PlotWindow
import time

#import pyqtgraph
#pyqtgraph.setConfigOption('background', 'w')
#pyqtgraph.setConfigOption('foreground', 'k')
LAST_ERROR_WINDOW_TIME = None
INTER_ERROR_TIME = 30

# http://www.riverbankcomputing.com/pipermail/pyqt/2009-May/022961.html
def excepthook(excType, excValue, tracebackobj):
    """
    Global function to catch unhandled exceptions.

    @param excType exception type
    @param excValue exception value
    @param tracebackobj traceback object
    """
    separator = '-' * 80
    logFile = "datamanagement.log"
    notice = \
        """An unhandled exception occurred. Please report the problem\n""" \
        """Error reporting has been silenced for the next 30s. To see all errors check the log\n""" \
        """A log has been written to "%s".\n\nError information:\n""" % (logFile)
    versionInfo="0.0.1"
    timeString = time.strftime("%Y-%m-%d, %H:%M:%S")


    tbinfofile = cStringIO.StringIO()
    traceback.print_tb(tracebackobj, None, tbinfofile)
    tbinfofile.seek(0)
    tbinfo = tbinfofile.read()
    errmsg = '%s: \n%s' % (str(excType), str(excValue))
    sections = [separator, timeString, separator, errmsg, separator, tbinfo]
    msg = '\n'.join(sections)
    try:
        f = open(logFile, "w")
        f.write(msg)
        f.write(versionInfo)
        f.close()
    except IOError:
        pass
    cur_time = time.time()
    global LAST_ERROR_WINDOW_TIME, INTER_ERROR_TIME
    if LAST_ERROR_WINDOW_TIME is None or cur_time - LAST_ERROR_WINDOW_TIME > INTER_ERROR_TIME:
        LAST_ERROR_WINDOW_TIME = cur_time
        errorbox = Qt.QMessageBox()
        errorbox.setText(str(notice)+str(msg)+str(versionInfo))
        errorbox.exec_()

def start():
    #sys.excepthook = excepthook
    app = Qt.QApplication([])
    win = PlotWindow()
    win.show()
    win.showMaximized()
    app.connect(app, Qt.SIGNAL("lastWindowClosed()"), win, Qt.SIGNAL("lastWindowClosed()"))
    return app.exec_()


if __name__ == "__main__":
    sys.exit(start())
