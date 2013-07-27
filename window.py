import time
from PyQt4 import Qt
from widgets import *
import objectsharer as objsh


class WindowDataGroup:
    def __init__(self, name, parent, proxy=None, attrs=None):
        self.name = name
        self.parent = parent
        self.proxy = proxy if proxy is not None else parent.proxy
        self.children = []
        self.is_dataset = False

        if parent is None:
            self.path = (name,)
        else:
            self.path = parent.path + (name,)

        if self.attrs is not None:
            self.attrs = attrs
        else:
            self.attrs = {}


class WindowDataSet(WindowDataGroup):
    def __init__(self, name, parent, proxy=None, attrs=None):
        WindowDataGroup.__init__(self, name, parent, proxy, attrs=attrs)
        self.is_dataset = True
        del self.children # DataSets have no children

        self.data = self.proxy[:]
        self.plot = RankNItemWidget(self.get_rank(), self.path)

        self.multiplots = []
        self.parametric_plots = []

    def update_data(self):
        self.data = self.proxy[:]
        self.plot.update_plot(self.data)

    def get_rank(self):
        if self.data is None or len(self.data) == 0:
            return None

        if self.is_parametric():
            return len(self.data[0]) - 1
        else:
            return len(self.data.shape)

    def is_parametric(self):
        return self.attrs.get('parametric', False)

class WindowInterface:
    def __init__(self, window):
        self.win = window

# Removed from widgets, move to window
        #self.dock_area = dock_area
        #self.dock_area.add_dock_auto_location(self)

    #def toggle_hide(self):
    #    #self.setVisible(not(self.isVisible()))
    #    if self.visible:
    #        self.setParent(None)
    #        self.label.setParent(None)
    #        self.visible = False
    #    else:
    #        self.dock_area.add_dock_auto_location(self)
    #        self.visible = True


class PlotWindow(Qt.QMainWindow):
    def __init__(self):
        Qt.QMainWindow.__init__(self)
        self.setup_ui()
        self.data_groups = {}

    def setup_ui(self):
        self.structure_tree = Qt.QTreeWidget()
        self.structure_tree.setColumnCount(4)
        self.structure_tree.setHeaderLabels(['Name', 'Shape', 'Save?', 'Plot?'])
        self.structure_tree.itemClicked.connect(self.change_edit_widget)
        self.structure_tree.itemDoubleClicked.connect(self.toggle_item)
        self.structure_tree.itemSelectionChanged.connect(self.configure_tree_buttons)
        self.structure_tree.setSelectionMode(Qt.QAbstractItemView.ExtendedSelection)
        self.structure_tree.setColumnWidth(0, 200)
        self.structure_tree.setColumnWidth(1, 50)
        self.structure_tree.setColumnWidth(2, 50)
        self.structure_tree.setColumnWidth(3, 50)

        self.dock_area = MyDockArea()
        self.max_plots_spinner = Qt.QSpinBox()
        self.max_plots_spinner.setValue(6)
        max_plots_widget = Qt.QWidget()
        max_plots_widget.setLayout(Qt.QHBoxLayout())
        max_plots_widget.layout().addWidget(Qt.QLabel('Maximum Plot Count'))
        max_plots_widget.layout().addWidget(self.max_plots_spinner)
        #self.save_button = Qt.QPushButton('Save Selection')
        #self.save_button.clicked.connect(self.save_selection)
        #self.save_button.setEnabled(False)
        self.multiplot_button = Qt.QPushButton('Plot Multiple Items')
        self.multiplot_button.clicked.connect(self.add_multiplot)
        self.multiplot_button.setEnabled(False)
        #self.remove_button = Qt.QPushButton('Remove Selection')
        #self.remove_button.clicked.connect(self.remove_selection)
        #self.remove_button.setEnabled(False)
        self.parametric_button = Qt.QPushButton('Plot Pair Parametrically')
        self.parametric_button.clicked.connect(lambda: self.add_multiplot(parametric=True))
        self.parametric_button.setEnabled(False)

        self.setCentralWidget(Qt.QSplitter())
        self.sidebar = sidebar = Qt.QWidget()
        sidebar.setLayout(Qt.QVBoxLayout())
        sidebar.layout().addWidget(max_plots_widget)
        sidebar.layout().addWidget(self.structure_tree)
        #sidebar.layout().addWidget(self.save_button)
        sidebar.layout().addWidget(self.multiplot_button)
        #sidebar.layout().addWidget(self.remove_button)
        sidebar.layout().addWidget(self.parametric_button)
        self.centralWidget().addWidget(sidebar)
        self.centralWidget().addWidget(self.dock_area)
        self.centralWidget().setSizes([300, 1000])
        self.current_edit_widget = None

        file_menu = self.menuBar().addMenu('File')
        #Ifile_menu.addAction('Save').triggered.connect(lambda checked: self.background_client.save_all())
        file_menu.addAction('Load').triggered.connect(lambda checked: self.load())
        file_menu.addAction('Load (readonly)').triggered.connect(lambda checked: self.load(readonly=True))
        #file_menu.addAction('Clear').triggered.connect(lambda checked: self.background_client.clear_all_data())

        self.message_box = Qt.QTextEdit()
        self.message_box.setReadOnly(True)
        self.message_box.setVisible(False)
        self.centralWidget().addWidget(self.message_box)
        debug_menu = self.menuBar().addMenu('Debug')
        action = debug_menu.addAction('View Debug Panel')
        action.setCheckable(True)
        action.setChecked(False)
        action.triggered.connect(self.message_box.setVisible)

    def setup_shared_objects(self):
        zbe = objsh.ZMQBackend()
        zbe.start_server('127.0.0.1', 7777)
        zbe.connect_to('tcp://127.0.0.1:55556')
        self.dataserver = objsh.helper.find_object('dataserver')
        self.dataserver.connect('changed', self.get_data_changed)
        public_interface = WindowInterface(self)
        objsh.register(public_interface, 'plotwin')
        zbe.add_qt_timer()

    def get_data_changed(self, file, path):
        if path not in self.data_groups: # Then create it
            if len(path) > 1 and path[:-1] not in self.data_groups:
                self.create_group(path[:-1]) # Create parent
            parent = self.data_groups[path[:-1]]
            child = WindowDataSet(path[-1], parent)
            self.data_groups[path] = child
            parent.children.append(child)

        else:
            self.data_groups[path].update_data()

    def create_group(self, path):
        if len(path) == 1:
            filename = path[0]
            proxy = self.dataserver.get_file(filename)
            self.data_groups[path] = WindowDataGroup(filename, None, proxy)

        if path[:-1] not in self.data_groups:
            self.create_group(path[:-1])

        parent = self.data_groups[path[:-1]]
        child = WindowDataGroup(path[-1], parent)
        self.data_groups[path] = child
        parent.chidren.append(child)

    ##############
    # Multiplots #
    ##############

    def add_multiplot(self, parametric=False):
        selection = self.structure_tree.selectedItems()
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
        selection = self.structure_tree.selectedItems()
        save = len(selection) > 0
        multiplot = len(selection) > 1
        multiplot = multiplot and all(i.is_leaf() for i in selection)
        multiplot = multiplot and all(self.plot_widgets[i.path].rank == 1 for i in selection)
        remove = len(selection) > 0
        parametric = len(selection) == 2
        parametric = parametric and all(i.is_leaf() for i in selection)
        parametric = parametric and all(self.plot_widgets[i.path].rank == 1 for i in selection)
        self.save_button.setEnabled(save)
        self.multiplot_button.setEnabled(multiplot)
        self.remove_button.setEnabled(remove)
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

        root = self.structure_tree.invisibleRootItem()
        (item.parent() or root).removeChild(item)

        attr_widget = self.attrs_widgets.pop(path)
        attr_widget.close()
        attr_widget.destroy()

    #def load(self, readonly=False):
    #    filename = str(Qt.QFileDialog().getOpenFileName(self, 'Load HDF5 file',
    #                                                    config.h5file_directory, config.h5file_filter))
    #    if not filename:
    #        return
    #    self.background_client.load_h5file(filename, readonly=readonly)

    def add_tree_widget(self, path, data=False, shape=(), save=True, plot=True):
        if path in self.tree_widgets:
            if data: # Update the description
                self.tree_widgets[path].update_fields(shape, save, plot)
            return

        if path[:-1] not in self.tree_widgets: # Make parent if it doesn't exist
            self.add_tree_widget(path[:-1])

        if data:
            item = DataTreeLeafItem([path[-1], str(shape), str(save), str(plot)])
        else:
            item = DataTreeLeafItem([path[-1]])

        parent = item.parent() or self.structure_tree.invisibleRootItem()
        parent.addChild(item)
        parent.setExpanded(True)

        if not data:
            item.setFirstColumnSpanned(True)

        self.tree_widgets[path] = item

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

    def change_edit_widget(self, item, col):
        path = item.path
        if self.current_edit_widget is not None:
            self.current_edit_widget.hide()

        if path not in self.attrs_widgets:
            if item.is_leaf:
                widget = LeafEditWidget(path, {})
            else:
                widget = NodeEditWidget(path, {})
            self.sidebar.layout().addWidget(widget)
            self.attrs_widgets[path] = widget
        else:
            widget = self.attrs_widgets[path]
            widget.show()

        self.current_edit_widget = widget

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
        self.structure_tree.itemClicked.emit(self.tree_widgets[path], 0)
        self.current_edit_widget.commit_button.clicked.emit(False)

    def _test_show_hide(self, path):
        self.structure_tree.itemDoubleClicked.emit(self.tree_widgets[path], 0)
        time.sleep(1)
        self.structure_tree.itemDoubleClicked.emit(self.tree_widgets[path], 0)

    def _test_multiplot(self, paths, parametric=False):
        for p in paths:
            self.structure_tree.setItemSelected(self.tree_widgets[p], True)
        self.add_multiplot(parametric=parametric)

    def _test_save_selection(self, paths):
        for p in paths:
            self.structure_tree.setItemSelected(self.tree_widgets[p], True)
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
