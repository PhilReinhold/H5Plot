import time
from PyQt4 import Qt
from widgets import *
import objectsharer as objsh
import config
import pickle
import sys
import logging

logger = logging.getLogger("Plot Window")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(name)s:%(levelname)s:%(message)s')
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)

class DataTreeItem(object):
    """
    An object with a presence in the data tree
    """
    data_tree_widget = None
    attrs_widget_layout = None
    def __init__(self, name, parent=None, attrs=None):
        self.name = name
        self.parent = parent
        self.path = parent.path if parent is not None else ()
        self.path += (name,)
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

    def update_tree_item(self, shape="", visible=""):
        self.tree_item.setText(1, str(shape))
        self.tree_item.setText(2, str(visible))

    def update_attrs(self, attrs):
        self.attrs.update(attrs)
        self.attrs_widget.update(attrs)


class DataTreeWidgetItem(Qt.QTreeWidgetItem):
    """
    Subclass QTreeWidgetItem to give it a global identifier
    """
    def __init__(self, path, *args, **kwargs):
        Qt.QTreeWidgetItem.__init__(self, *args, **kwargs)
        self.path = path


class WindowDataGroup(DataTreeItem):
    """
    A Data Tree Item corresponding to a (remote) shared DataGroup
    """
    def __init__(self, name, parent, proxy=None, **kwargs):
        super(WindowDataGroup, self).__init__(name, parent, **kwargs)
        logger.debug('Initializing WindowDataGroup %s' % '/'.join(self.path))
        self.name = name
        self.parent = parent

        if proxy is None:
            if parent is None:
                raise ValueError("Top Level WindowDataGroups must be provided with a proxy")
            self.proxy = parent.proxy[name]
        else:
            self.proxy = proxy

        self.children = []
        self.attrs = self.proxy.get_attrs()


class WindowPlot(DataTreeItem):
    """
    A plot living in the Dock Area
    """
    def __init__(self, name, parent, **kwargs):
        super(WindowPlot, self).__init__(name, parent, **kwargs)
        if not hasattr(self, 'tree_item'):
            DataTreeItem.__init__(self, name, parent)
        self.data = None
        self.rank = None
        self.plot = None
        self.attrs = {}

        self.multiplots = []
        self.parametric_plots = []

    def set_data(self, data):
        self.data = data
        self.rank = self.get_rank()
        if self.plot is None:
            self.plot = RankNItemWidget(self.rank, self.path)
        self.plot.update(self.data, self.attrs)

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
        logger.debug('Initializing WindowDataSet %s' % '/'.join(self.path))
        self.children = None
        self.update_data()

    def update_data(self):
        logger.debug('Updating data at %s' % '/'.join(self.path))
        self.data = self.proxy[:]
        self.set_data(self.data)
        self.update_tree_item(shape=self.data.shape)

    def update_attrs(self, attrs):
        super(WindowDataSet, self).update_attrs(attrs)
        if any(key in self.plot.plot_attrs for key in attrs.keys()):
            self.plot.update(self.data, self.attrs)


class WindowInterface:
    """
    Shareable wrapper for a PlotWindow.
    """
    def __init__(self, window):
        self.win = window

    def plot(self, name, data):
        pass

    def quit(self):
        sys.exit()


class PlotWindow(Qt.QMainWindow):
    def __init__(self):
        Qt.QMainWindow.__init__(self)
        self.setup_ui()
        self.data_groups = {}
        self.setup_shared_objects()

    def setup_ui(self):
        # Sidebar / Dockarea
        self.setCentralWidget(Qt.QSplitter())
        self.sidebar = Qt.QWidget()
        self.sidebar.setLayout(Qt.QVBoxLayout())
        self.dock_area = MyDockArea()
        ItemWidget.dock_area = self.dock_area
        self.centralWidget().addWidget(self.sidebar)
        self.centralWidget().addWidget(self.dock_area)
        self.centralWidget().setSizes([300, 1000])

        # Server-Oriented Buttons
        self.connect_dataserver_button = Qt.QPushButton('Connect to Data Server')
        self.connect_dataserver_button.clicked.connect(self.connect_dataserver)
        self.sidebar.layout().addWidget(self.connect_dataserver_button)

        # File-Oriented Buttons
        self.load_file_button = Qt.QPushButton('Load File')
        self.save_view_button = Qt.QPushButton('Save View')
        self.load_view_button = Qt.QPushButton('Load View')
        self.sidebar.layout().addWidget(self.load_file_button)
        self.sidebar.layout().addWidget(self.save_view_button)
        self.sidebar.layout().addWidget(self.load_view_button)

        # Spinner setting number of plots to display simultaneously by default
        self.max_plots_spinner = Qt.QSpinBox()
        self.max_plots_spinner.setValue(6)
        max_plots_widget = Qt.QWidget()
        max_plots_widget.setLayout(Qt.QHBoxLayout())
        max_plots_widget.layout().addWidget(Qt.QLabel('Maximum Plot Count'))
        max_plots_widget.layout().addWidget(self.max_plots_spinner)
        self.sidebar.layout().addWidget(max_plots_widget)

        # Structure Tree
        self.data_tree_widget = Qt.QTreeWidget()
        self.data_tree_widget.setColumnCount(4)
        self.data_tree_widget.setHeaderLabels(['Name', 'Shape', 'Save?', 'Plot?'])
        self.data_tree_widget.itemClicked.connect(self.change_edit_widget)
        self.data_tree_widget.itemDoubleClicked.connect(self.toggle_item)
        self.data_tree_widget.itemSelectionChanged.connect(self.configure_tree_buttons)
        self.data_tree_widget.setSelectionMode(Qt.QAbstractItemView.ExtendedSelection)
        self.data_tree_widget.setColumnWidth(0, 90)
        self.data_tree_widget.setColumnWidth(1, 50)
        self.data_tree_widget.setColumnWidth(2, 50)
        self.data_tree_widget.setColumnWidth(3, 50)
        DataTreeItem.data_tree_widget = self.data_tree_widget
        self.sidebar.layout().addWidget(self.data_tree_widget)

        # Plot-Oriented Buttons
        self.multiplot_button = Qt.QPushButton('Plot Multiple Items')
        self.multiplot_button.clicked.connect(self.add_multiplot)
        self.multiplot_button.setEnabled(False)
        self.parametric_button = Qt.QPushButton('Plot Pair Parametrically')
        self.parametric_button.clicked.connect(lambda: self.add_multiplot(parametric=True))
        self.parametric_button.setEnabled(False)
        self.sidebar.layout().addWidget(self.multiplot_button)
        self.sidebar.layout().addWidget(self.parametric_button)
        self.current_edit_widget = None

        # Attribute Editor Area
        attrs_widget_box = Qt.QWidget()
        attrs_widget_box.setLayout(Qt.QVBoxLayout())
        DataTreeItem.attrs_widget_layout = attrs_widget_box.layout()
        self.current_edit_widget = None
        self.sidebar.layout().addWidget(attrs_widget_box)

        # Status Bar
        self.view_status = Qt.QLabel('Empty')
        self.current_files = None
        self.statusBar().addWidget(self.view_status)

        # Menu bar
        #file_menu = self.menuBar().addMenu('File')
        #Ifile_menu.addAction('Save').triggered.connect(lambda checked: self.background_client.save_all())
        #file_menu.addAction('Load').triggered.connect(lambda checked: self.load())
        #file_menu.addAction('Load (readonly)').triggered.connect(lambda checked: self.load(readonly=True))
        #file_menu.addAction('Clear').triggered.connect(lambda checked: self.background_client.clear_all_data())

        # Message Box
        self.message_box = Qt.QTextEdit()
        self.message_box.setReadOnly(True)
        self.message_box.setVisible(False)
        self.centralWidget().addWidget(self.message_box)
        debug_menu = self.menuBar().addMenu('Debug')
        action = debug_menu.addAction('View Debug Panel')
        action.setCheckable(True)
        action.setChecked(False)
        action.triggered.connect(self.message_box.setVisible)

    #######################
    # Data Server Actions #
    #######################

    def setup_shared_objects(self):
        self.zbe = objsh.ZMQBackend()
        self.zbe.start_server('127.0.0.1', 55563)
        self.connect_dataserver()
        #zbe.connect_to('tcp://127.0.0.1:55556')
        public_interface = WindowInterface(self)
        objsh.register(public_interface, 'plotwin')
        self.zbe.add_qt_timer()

    def connect_dataserver(self):#, addr='127.0.0.1', port=55556):
        try:
            addr = '127.0.0.1'
            port = 55556
            self.zbe.refresh_connection('tcp://%s:%d' % (addr, port))
            self.dataserver = objsh.helper.find_object('dataserver')
            self.dataserver.connect('data-changed', self.get_data_changed)
            self.dataserver.connect('attrs-changed', self.get_attrs_changed)
        except ValueError:
            Qt.QMessageBox(Qt.QMessageBox.Warning, "Connection Failed", "Could not connect to dataserver").exec_()
            return

    def get_data_changed(self, filename, pathname):
        path = (filename,) + tuple(pathname.split('/')[1:])
        logger.debug('Data Changed at %s' % '/'.join(path))
        path = tuple(path)
        if path not in self.data_groups: # Then create it
            logger.debug('Path not found: %s' % '/'.join(path))
            logger.debug(repr(self.data_groups))
            if path[:-1] not in self.data_groups:
                self.create_group(path[:-1]) # Create parent if necessary
            parent = self.data_groups[path[:-1]]
            child = WindowDataSet(path[-1], parent)
            self.data_groups[path] = child
            parent.children.append(child)

        else:
            print 'Path found', path, 'updating...'
            self.data_groups[path].update_data()

    def create_group(self, path):
        logger.debug('Create Group! %s' % '/'.join(path))
        if len(path) == 1:
            filename = path[0]
            proxy = self.dataserver.get_file(filename)
            self.data_groups[path] = WindowDataGroup(filename, None, proxy)
            return

        if path[:-1] not in self.data_groups:
            self.create_group(path[:-1])

        parent = self.data_groups[path[:-1]]
        child = WindowDataGroup(path[-1], parent)
        self.data_groups[path] = child
        parent.chidren.append(child)

    def get_attrs_changed(self, filename, pathname, attrs):
        logger.debug('Attrs received for %s %s' % (filename, pathname))
        path = (filename,) + tuple(pathname.split('/')[1:])
        self.data_groups[path].update_attrs(attrs)

    ####################
    # Attribute Editor #
    ####################

    def change_edit_widget(self, item, col):
        logger.debug('Changing edit widget to %s' % '/'.join(item.path))
        if self.current_edit_widget is not None:
            self.current_edit_widget.hide()

        widget = self.data_groups[item.path].attrs_widget
        self.current_edit_widget = widget
        widget.show()

    ################
    # File Buttons #
    ################

    def load(self):
        filename = str(Qt.QFileDialog().getOpenFileName(self, 'Load HDF5 file',
                                                        config.h5file_directory, config.h5file_filter))
        if not filename:
            return
        proxy = self.dataserver.get_file(filename)
        self.data_groups[(filename,)] = WindowDataGroup(filename, None, proxy=proxy)

    def save_view(self):
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
        paths = tuple(item.strpath for item in selection)
        if parametric:
            widget = ParametricItemWidget(selection[0].path, selection[1].path, self.dock_area)
            self.parametric_widgets[paths] = widget
        else:
            widget = MultiplotItemWidget('::'.join(paths), self.dock_area)
            self.multiplot_widgets[paths] = widget
        widget.remove_button.clicked.connect(lambda: self.remove_multiplot(paths, parametric=parametric))
        for item in selection:
            self.multiplots[item.strpath].append(widget)
            #self.background_client.update_plot(item.path)
        self.regulate_plot_count()

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

    def configure_tree_buttons(self):
        selection = self.data_tree_widget.selectedItems()
        multiplot = len(selection) > 1
        multiplot = multiplot and all(i.is_leaf() for i in selection)
        multiplot = multiplot and all(self.plot_widgets[i.path].rank == 1 for i in selection)
        parametric = len(selection) == 2
        parametric = parametric and all(i.is_leaf() for i in selection)
        parametric = parametric and all(self.plot_widgets[i.path].rank == 1 for i in selection)
        self.multiplot_button.setEnabled(multiplot)
        self.parametric_button.setEnabled(parametric)

    #def remove_selection(self):
    #    for item in self.structure_tree.selectedItems():
    #        # This is a little complicated. We need to remove the data from the background.
    #        # Removing it from the background, however, can also be done through a client.
    #        # Removing it from a client should trigger removal of the plots from the window.
    #        # Therefore, the chain of control in this command is
    #        # Window.remove_selection --> Background.remove_item --> Window.remove_item
    #        # Sorry.
    #        self.background_client.remove_item(item.path)

    def remove_item(self, path):
        item = self.tree_widgets[path]

        if item.is_leaf():
            print 'window.remove_item', path
            widget = self.plot_widgets.pop(item.path)
            widget.visible = False
            widget.close()
            widget.destroy() # This might be voodoo

        if item.parent() and item.parent().childCount == 1:
            self.remove_item(path[:-1])

        root = self.data_tree_widget.invisibleRootItem()
        (item.parent() or root).removeChild(item)

        attr_widget = self.attrs_widgets.pop(path)
        attr_widget.close()
        attr_widget.destroy()

    def toggle_path(self, path):
        self.toggle_item(self.tree_widgets[path], 0)

    def toggle_item(self, item, col):
        if item.is_leaf():# and item.plot:
            widget = self.plot_widgets[item.path]
            widget.toggle_hide()
            #self.background_client.set_params(item.path, widget.rank, plot=widget.visible)
            print 'toggled', item.path
        else:
            for child in item.getChildren():
                self.toggle_item(child, col)

    def add_plot_widget(self, path, rank=1, **kwargs):
        if path in self.plot_widgets:
            raise ValueError('Plot %s already exists in window' % (path,))
        strpath = "/".join(path)
        if rank == 1:
            item = Rank1ItemWidget(strpath, self.dock_area, **kwargs)
        elif rank == 2:
            item = Rank2ItemWidget(strpath, self.dock_area, **kwargs)
        else:
            raise ValueError('Rank must be either 1 or 2, not ' + str(rank))

        #item.clear_button.clicked.connect(lambda: self.background_client.clear_data(path))
        #item.remove_button.clicked.connect(lambda: self.background_client.set_params(path, rank, plot=False))
        self.register_param('update'+strpath, item.update_toggle)
        self.plot_widgets[path] = item
        self.plot_widgets_update_log[path] = time.time()
        self.regulate_plot_count()

    def regulate_plot_count(self):
        widgets = list(self.plot_widgets.values()) + list(self.multiplot_widgets.values()) + list(self.parametric_widgets.values())
        if len(filter(lambda w: w.visible, widgets)) > self.max_plots_spinner.value():
            for p, t in sorted(self.plot_widgets_update_log.items(), key=lambda x: x[1]):
                if self.plot_widgets[p].visible:
                    self.toggle_item(self.tree_widgets[p], 0)
                    break

    def _test_edit_widget(self, path):
        self.data_tree_widget.itemClicked.emit(self.tree_widgets[path], 0)
        self.current_edit_widget.commit_button.clicked.emit(False)

    def _test_show_hide(self, path):
        self.data_tree_widget.itemDoubleClicked.emit(self.tree_widgets[path], 0)
        time.sleep(1)
        self.data_tree_widget.itemDoubleClicked.emit(self.tree_widgets[path], 0)

    def _test_multiplot(self, paths, parametric=False):
        for p in paths:
            self.data_tree_widget.setItemSelected(self.tree_widgets[p], True)
        self.add_multiplot(parametric=parametric)

    def _test_save_selection(self, paths):
        for p in paths:
            self.data_tree_widget.setItemSelected(self.tree_widgets[p], True)
        self.save_selection()


    def msg(self, *args):
        self.message_box.append(', '.join(map(str, args)))

    def wait_for_cleanup_dialog(self):
        """
        :return: None
        Activated when the window is closed, this displays a dialog until the background
        """
        dialog = Qt.QDialog()
        dialog.setLayout(Qt.QVBoxLayout())
        dialog.layout().addWidget(Qt.QLabel("Please wait while the server cleans up..."))
        self.connect(self.background_obj, Qt.SIGNAL('server done'), dialog.accept)
        self.connect(self.background_obj, Qt.SIGNAL('server done'), self.background_thread.exit)
        dialog.exec_()

widget_tools = {
    Qt.QSpinBox : {
        "read" : "value",
        "change_signal" : "valueChanged"},
    Qt.QDoubleSpinBox : {
        "read" : "value",
        "change_signal" : "valueChanged"},
    Qt.QLineEdit : {
        "read" : "text",
        "change_signal" : "textEdited"},
    Qt.QButtonGroup : {
        "read" : "checkedId",
        "change_signal" : "buttonClicked"},
    Qt.QCheckBox : {
        "read" : "isChecked",
        "change_signal" : "stateChanged"},
    Qt.QSlider : {
        "read" : "value",
        "change_signal" : "valueChanged"},
    }

def run_plotwindow():
    #sys.excepthook = excepthook
    app = Qt.QApplication([])
    win = PlotWindow()
    win.show()
    #win.showMaximized()
    win.setMinimumSize(700, 500)
    app.connect(app, Qt.SIGNAL("lastWindowClosed()"), win, Qt.SIGNAL("lastWindowClosed()"))
    return app.exec_()


if __name__ == "__main__":
    sys.exit(run_plotwindow())
