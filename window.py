import time
from PyQt4 import Qt
from widgets import *
import objectsharer as objsh
import config
import pickle
import sys
import logging
import traceback

logger = logging.getLogger("Plot Window")
logger.setLevel(logging.WARNING)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(name)s:%(levelname)s:%(message)s')
handler.setLevel(logging.WARNING)
handler.setFormatter(formatter)
logger.addHandler(handler)

from dataserver import DATA_DIRECTORY
h5file_directory = DATA_DIRECTORY
h5file_filter = 'HDF5 Files (*.h5)'


class WindowItem(object):
    """
    An object with a presence in the data tree
    """
    registry = {}
    data_tree_widget = None
    attrs_widget_layout = None
    def __init__(self, name, parent=None, attrs=None):
        self.name = name
        self.parent = parent
        self.children = {}
        if parent is not None:
            parent.children[name] = self
        self.path = parent.path if parent is not None else ()
        self.path += (name,)
        assert self.path not in WindowItem.registry, self.path + " already exists"
        self.strpath = '/'.join(self.path)
        WindowItem.registry[self.path] = self
        self.tree_item = DataTreeWidgetItem(self.path, [name, "", ""])

        if attrs is None:
            self.attrs = {}
        else:
            self.attrs = attrs

        self.attrs_widget = NodeEditWidget(self.path, self.attrs)
        self.attrs_widget.setVisible(False)
        self.attrs_widget_layout.addWidget(self.attrs_widget)

        if parent is None:
            self.data_tree_widget.addTopLevelItem(self.tree_item)
        else:
            parent.tree_item.addChild(self.tree_item)
            parent.tree_item.setExpanded(True)

    def update_tree_item(self, shape=None, visible=None):
        if shape is not None:
            self.tree_item.setText(1, str(shape))
        if visible is not None:
            self.tree_item.setText(2, str(visible))

    def update_attrs(self, attrs):
        self.attrs.update(attrs)
        self.attrs_widget.update_attrs(attrs)

    def remove(self):
        del self.tree_item
        del self.attrs_widget


class DataTreeWidgetItem(Qt.QTreeWidgetItem):
    """
    Subclass QTreeWidgetItem to give it a globally recognized identifier
    """
    def __init__(self, path, *args, **kwargs):
        Qt.QTreeWidgetItem.__init__(self, *args, **kwargs)
        self.path = path
        self.strpath = '/'.join(self.path)

    def is_leaf(self):
        return self.childCount() == 0

    def get_children(self):
        for i in range(self.childCount()):
            yield self.child(i)


class WindowDataGroup(WindowItem):
    """
    A Data Tree Item corresponding to a (remote) shared DataGroup
    """
    def __init__(self, name, parent, proxy=None, **kwargs):
        super(WindowDataGroup, self).__init__(name, parent, **kwargs)
        logger.debug('Initializing WindowDataGroup %s' % self.strpath)

        if proxy is None:
            if parent is None:
                raise ValueError("Top Level WindowDataGroups must be provided with a proxy")
            self.proxy = parent.proxy[name]
        else:
            self.proxy = proxy
        self.attrs_widget.set_proxy(self.proxy)

        self.attrs = self.proxy.get_attrs()
        self.update_attrs(self.attrs)

        if not self.is_dataset():
            self.children = {}
            for name in self.proxy.keys():
                self.update_child(name)

            self.proxy.connect('changed', self.update_child)
            self.proxy.connect('group-added', self.add_group)
            #TODO connect removed

        self.proxy.connect('attrs-changed', self.update_attrs)

    def is_dataset(self):
        return isinstance(self, WindowDataSet)

    def update_child(self, key):
        if key not in self.children:
            if hasattr(self.proxy[key], 'keys'):
                self.add_group(key=key)
                return
            else:
                self.add_dataset(key)
        if hasattr(self.children[key], 'update_data'): # Confusing to me...
            self.children[key].update_data()

    def add_group(self, key):
        path = self.path + (key,)
        if path in WindowItem.registry:
            item = WindowItem.registry[path]
            item.proxy = self.proxy[key]
            return

        g = WindowDataGroup(key, self)
        for key in g.proxy.keys():
            g.update_child(key)

    def add_dataset(self, key):
        WindowDataSet(key, self)

class WindowPlot(WindowItem):
    """
    A plot living in the Dock Area
    """
    def __init__(self, name, parent, **kwargs):
        super(WindowPlot, self).__init__(name, parent, **kwargs)
        self.data = None
        self.rank = None
        self.plot = None

        objsh.register(self, self.strpath)

    def set_data(self, data):
        self.data = np.array(data)
        self.rank = self.get_rank()

        default_attrs = {
            'x0': 0,
            'xscale': 1,
            'xlabel': 'X',
            'ylabel': 'Y',
        }
        if self.rank is 2:
            default_attrs.update({
                'y0': 0,
                'yscale': 1,
                'zlabel': 'Z',
            })
        # Update, but don't overwrite
        self.update_attrs(
            {k: v for k, v in default_attrs.items() if k not in self.attrs}
        )

        if self.plot is None:
            if self.rank is 1:
                self.plot = Rank1ItemWidget(self)
            elif self.rank is 2:
                self.plot = Rank2ItemWidget(self)
            else:
                raise Exception('No rank ' + str(self.rank) + ' item widget')

        self.plot.update_plot(self.data, self.attrs)
        self.emit('data-changed')
        self.update_tree_item(shape=self.data.shape, visible=self.plot.is_visible())

    def set_attrs(self, attrs):
        self.attrs = attrs

    def is_parametric(self):
        return self.attrs.get('parametric', False)

    def get_rank(self):
        if self.data is None or len(self.data) == 0:
            return None
        elif self.is_parametric():
            return len(self.data[0]) - 1
        else:
            return len(self.data.shape)

    def remove(self):
        super(WindowPlot, self).remove()
        objsh.helper.unregister(self)
        if self.plot.is_visible():
            self.plot.toggle_hide()
        del self.plot

class WindowMultiPlot(WindowItem):
    def __init__(self, sources, parametric=False):
        connector = " vs " if parametric else " :: "
        name = connector.join(i.name for i in sources)

        if ("multiplots",) not in WindowItem.registry:
            WindowItem("multiplots", None)

        multiplots_group = WindowItem.registry[("multiplots",)]
        WindowItem.__init__(self, name, multiplots_group)

        if parametric:
            self.plot = ParametricItemWidget(sources[0].path, sources[1].path)
        else:
            self.plot = MultiplotItemWidget(name)
            self.plot.line_plt.addLegend()

        for source in sources:
            self.update_source(source.path)
            source.connect('data-changed', lambda: self.update_source(source.path))

    def update_source(self, path):
        item = WindowItem.registry[path]
        self.plot.update_path(path, item.data, item.attrs)


class WindowDataSet(WindowDataGroup, WindowPlot):
    """
    A WindowPlot which is kept in sync with a shared h5py DataSet
    :param name: TODO
    :param parent:
    :param proxy:
    :param attrs:
    """
    def __init__(self, name, parent, **kwargs):
        super(WindowDataSet, self).__init__(name, parent, **kwargs)
        logger.debug('Initializing WindowDataSet %s' % self.strpath)
        self.update_data()

    def update_data(self):
        logger.debug('Updating data at %s' % self.strpath)
        self.data = self.proxy[:]
        if len(self.data) > 0:
            self.set_data(self.data)

    def update_attrs(self, attrs):
        super(WindowDataSet, self).update_attrs(attrs)
        if self.plot and any(key in self.plot.plot_attrs for key in attrs.keys()):
            self.plot.update_plot(self.data, self.attrs)


class WindowInterface:
    """
    Shareable wrapper for a PlotWindow.
    """
    def __init__(self, window):
        self.win = window
        objsh.register(self, 'plotwin')

    def get_all_plots(self):
        return { k: v for k, v in WindowItem.registry.items() if isinstance(v, WindowPlot) }

    def add_plot(self, name):
        if (name,) in WindowItem.registry:
            return WindowItem.registry[(name,)]
        return WindowPlot(name, None)

    def quit(self):
        sys.exit()


class PlotWindow(Qt.QMainWindow):
    """
    A window for viewing and plotting DataSets and DataGroups shared by a DataServer
    """
    def __init__(self):
        Qt.QMainWindow.__init__(self)
        self.setup_ui()
        #self.data_groups = {}
        self.setup_server()

    def setup_ui(self):
        # Sidebar / Dockarea
        self.setCentralWidget(Qt.QSplitter())
        self.sidebar = Qt.QWidget()
        self.sidebar.setLayout(Qt.QVBoxLayout())
        self.dock_area = MyDockArea()
        ItemWidget.dock_area = self.dock_area
        self.centralWidget().addWidget(self.sidebar)
        self.centralWidget().addWidget(self.dock_area)
        self.centralWidget().setSizes([250, 1000])

        # Spinner setting number of plots to display simultaneously by default
        self.max_plots_spinner = Qt.QSpinBox()
        self.max_plots_spinner.setValue(4)
        self.max_plots_spinner.valueChanged.connect(self.dock_area.set_max_plots)
        max_plots_widget = Qt.QWidget()
        max_plots_widget.setLayout(Qt.QHBoxLayout())
        max_plots_widget.layout().addWidget(Qt.QLabel('Maximum Plot Count'))
        max_plots_widget.layout().addWidget(self.max_plots_spinner)
        self.sidebar.layout().addWidget(max_plots_widget)

        # Structure Tree
        self.data_tree_widget = Qt.QTreeWidget()
        self.data_tree_widget.setColumnCount(3)
        self.data_tree_widget.setHeaderLabels(['Name', 'Shape', 'Visible?'])
        self.data_tree_widget.itemClicked.connect(self.change_edit_widget)
        self.data_tree_widget.itemDoubleClicked.connect(self.toggle_item)
        self.data_tree_widget.itemSelectionChanged.connect(self.configure_tree_actions)
        self.data_tree_widget.setSelectionMode(Qt.QAbstractItemView.ExtendedSelection)
        self.data_tree_widget.setColumnWidth(0, 90)
        self.data_tree_widget.setColumnWidth(1, 50)
        self.data_tree_widget.setColumnWidth(2, 50)
        self.data_tree_widget.setColumnWidth(3, 50)
        WindowItem.data_tree_widget = self.data_tree_widget
        self.sidebar.layout().addWidget(self.data_tree_widget)

        # Structure Tree Context Menu
        self.multiplot_action = Qt.QAction('Create Multiplot', self)
        self.multiplot_action.triggered.connect(self.add_multiplot)
        self.data_tree_widget.addAction(self.multiplot_action)
        self.parametric_action = Qt.QAction('Plot Pair Parametrically', self)
        self.parametric_action.triggered.connect(lambda: self.add_multiplot(True))
        self.data_tree_widget.addAction(self.parametric_action)
        self.data_tree_widget.setContextMenuPolicy(Qt.Qt.ActionsContextMenu)

        # Attribute Editor Area
        attrs_widget_box = Qt.QWidget()
        attrs_widget_box.setLayout(Qt.QVBoxLayout())
        WindowItem.attrs_widget_layout = attrs_widget_box.layout()
        self.current_edit_widget = None
        self.sidebar.layout().addWidget(attrs_widget_box)

        # Status Bar
        self.connected_status = Qt.QLabel('Not Connected')
        #self.view_status = Qt.QLabel('Empty')
        self.current_files = None
        self.statusBar().addWidget(self.connected_status)
        #self.statusBar().addWidget(self.view_status)

        self.connection_checker = Qt.QTimer()
        self.connection_checker.timeout.connect(self.check_connection_status)

        # Menu bar
        file_menu = self.menuBar().addMenu('File')
        self.connect_to_server_action = Qt.QAction('Connect to Dataserver', self)
        self.connect_to_server_action.triggered.connect(lambda checked: self.connect_dataserver())
        file_menu.addAction(self.connect_to_server_action)
        self.load_file_action = Qt.QAction('Load File', self)
        self.load_file_action.triggered.connect(lambda checked: self.load_file())
        file_menu.addAction(self.load_file_action)

    #######################
    # Data Server Actions #
    #######################

    def setup_server(self):
        self.zbe = objsh.ZMQBackend()
        self.zbe.start_server('127.0.0.1', 55563)
        try:
            self.connect_dataserver()
        except objsh.TimeoutError:
            logger.warning('Could not connect to dataserver on startup')
        self.public_interface = WindowInterface(self)
        self.zbe.add_qt_timer()

    def connect_dataserver(self):#, addr='127.0.0.1', port=55556):
        addr = '127.0.0.1'
        port = 55556
        self.zbe.refresh_connection('tcp://%s:%d' % (addr, port))
        self.dataserver = objsh.helper.find_object('dataserver', no_cache=True)
        self.dataserver.connect('file-added', self.add_file)
        for filename, proxy in self.dataserver.list_files(names_only=False).items():
            self.add_file(filename, proxy)
        self.connected_status.setText('Connected to tcp://%s:%d' % (addr, port))
        self.connect_to_server_action.setEnabled(False)
        self.load_file_action.setEnabled(True)
        #self.connection_checker.start(3000)

    def check_connection_status(self):
        try:
            self.dataserver.hello(timeout=50)
        except objsh.TimeoutError:
            self.connected_status.setText('Not Connected')
            self.connect_to_server_action.setEnabled(True)
            self.load_file_action.setEnabled(False)
            self.connection_checker.stop()

    def add_file(self, filename, proxy=None):
        if proxy is None:
            proxy = self.dataserver.get_file(filename)
        if (filename,) in WindowItem.registry:
            WindowItem.registry[(filename,)].remove()
        WindowDataGroup(filename, None, proxy)

#    def get_data_changed(self, filename, pathname):
#        path = (filename,) + tuple(pathname.split('/')[1:])
#        logger.debug('Data Changed at %s' % '/'.join(path))
#        path = tuple(path)
#        if path not in self.data_groups: # Then create it
#            logger.debug('Path not found: %s' % '/'.join(path))
#            logger.debug(repr(self.data_groups))
#            if path[:-1] not in self.data_groups:
#                self.add_group(path[:-1]) # Create parent if necessary
#            parent = self.data_groups[path[:-1]]
#            child = WindowDataSet(path[-1], parent)
#            self.data_groups[path] = child
#
#        else:
#            print 'Path found', path, 'updating...'
#            self.data_groups[path].update_data()
#
#
#    def get_attrs_changed(self, filename, pathname, attrs):
#        logger.debug('Attrs received for %s %s' % (filename, pathname))
#        path = (filename,) + tuple(pathname.split('/')[1:])
#        self.data_groups[path].update_attrs(attrs)
#
    ####################
    # Attribute Editor #
    ####################

    def change_edit_widget(self, item, col):
        logger.debug('Changing edit widget to %s' % item.strpath)
        if self.current_edit_widget is not None:
            self.current_edit_widget.hide()

        widget = WindowItem.registry[item.path].attrs_widget
        self.current_edit_widget = widget
        widget.show()

    ################
    # File Buttons #
    ################

    def load_file(self):
        filename = str(Qt.QFileDialog().getOpenFileName(self, 'Load HDF5 file', h5file_directory, h5file_filter))
        if not filename:
            return
        self.dataserver.get_file(filename)

    def save_view(self): # TODO
        filename = str(Qt.QFileDialog().getSaveFileName(self, 'Save View file'))
        open_plots = []
        for group in self.data_groups.values():
            if group.plot.parent() is not None:
                open_plots.append(group.path)
        dock_state = self.dock_area.saveState()
        view_state = {
            'open_plots': open_plots,
            'dock_state': dock_state,
        }
        with open(filename, 'w') as f:
            pickle.Pickler(f).save(view_state)


    ##############
    # Multiplots #
    ##############

    def add_multiplot(self, parametric=False):
        selection = self.data_tree_widget.selectedItems()
        sources = [WindowItem.registry[i.path] for i in selection]
        WindowMultiPlot(sources, parametric)

        #if parametric:
        #    widget = ParametricItemWidget(selection[0].path, selection[1].path, self.dock_area)
        #    self.parametric_widgets[paths] = widget
        #else:
        #    widget = MultiplotItemWidget('::'.join(paths), self.dock_area)
        #    self.multiplot_widgets[paths] = widget
        #widget.remove_button.clicked.connect(lambda: self.remove_multiplot(paths, parametric=parametric))
        #for item in selection:
        #    self.multiplots[item.strpath].append(widget)
        #    #self.background_client.update_plot(item.path)

    def remove_multiplot(self, paths, parametric=False):
        if parametric:
            widget = self.parametric_widgets.pop(paths)
        else:
            widget = self.multiplot_widgets.pop(paths)
        for n in paths:
            self.multiplots[n].remove(widget)
        widget.setParent(None)

    def update_multiplots(self, path, leaf):
        for widget in self.multiplots['/'.join(path)]:
            widget.update_plot(path, leaf)

    def configure_tree_actions(self):
        selection = self.data_tree_widget.selectedItems()
        multiplot = len(selection) > 1
        multiplot = multiplot and all(i.is_leaf() for i in selection)
        multiplot = multiplot and all(WindowItem.registry[i.path].rank == 1 for i in selection)
        parametric = multiplot and len(selection) == 2
        #if parametric:
        #    item1, item2 = [WindowItem.registry[i.path] for i in selection]
        #    parametric = parametric and item1.data.shape[0] == item2.data.shape[0]
        self.multiplot_action.setEnabled(multiplot)
        self.parametric_action.setEnabled(parametric)

    #def remove_selection(self):
    #    for item in self.structure_tree.selectedItems():
    #        # This is a little complicated. We need to remove the data from the background.
    #        # Removing it from the background, however, can also be done through a client.
    #        # Removing it from a client should trigger removal of the plots from the window.
    #        # Therefore, the chain of control in this command is
    #        # Window.remove_selection --> Background.remove_item --> Window.remove_item
    #        # Sorry.
    #        self.background_client.remove_item(item.path)

    def toggle_path(self, path):
        self.toggle_item(self.tree_widgets[path], 0)

    def toggle_item(self, item, col):
        if item.is_leaf():# and item.plot:
            item = WindowItem.registry[item.path]
            item.plot.toggle_hide()
            item.update_tree_item(visible=item.plot.is_visible())
        else:
            for child in item.get_children():
                self.toggle_item(child, col)


#See http://stackoverflow.com/questions/2655354/how-to-allow-resizing-of-qmessagebox-in-pyqt4
class ResizeableMessageBox(Qt.QMessageBox):
    def __init__(self):
        Qt.QMessageBox.__init__(self)
        self.setSizeGripEnabled(True)

    def event(self, e):
        result = Qt.QMessageBox.event(self, e)

        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.setSizePolicy(Qt.QSizePolicy.Expanding, Qt.QSizePolicy.Expanding)

        textEdit = self.findChild(Qt.QTextEdit)
        if textEdit != None :
            textEdit.setMinimumHeight(0)
            textEdit.setMaximumHeight(16777215)
            textEdit.setMinimumWidth(0)
            textEdit.setMaximumWidth(16777215)
            textEdit.setSizePolicy(Qt.QSizePolicy.Expanding, Qt.QSizePolicy.Expanding)

        return result

def excepthook(error, instance, tb):
    msg_box = ResizeableMessageBox()
    msg_box.setText('Caught Exception of type ' + str(error).split("'")[1])
    msg_box.setInformativeText(str(instance))
    msg_box.setDetailedText("".join(traceback.format_tb(tb)))
    msg_box.exec_()


def run_plotwindow():
    sys.excepthook = excepthook
    app = Qt.QApplication([])
    win = PlotWindow()
    win.show()
    #win.showMaximized()
    win.setMinimumSize(700, 500)
    app.connect(app, Qt.SIGNAL("lastWindowClosed()"), win, Qt.SIGNAL("lastWindowClosed()"))
    return app.exec_()


if __name__ == "__main__":
    sys.exit(run_plotwindow())
