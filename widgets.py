from collections import defaultdict
from copy import copy
import warnings

from PyQt4 import Qt
import pyqtgraph
import pyqtgraph as pg
import pyqtgraph.dockarea
import numpy as np

import helpers

#Qt.QTreeWidgetItem.is_leaf = lambda item: str(item.text(1)) != ""
#Qt.QTreeWidgetItem.getChildren = lambda item: [item.child(i) for i in range(item.childCount())]

class MyDockArea(pyqtgraph.dockarea.DockArea):
    def __init__(self, *args, **kwargs):
        pyqtgraph.dockarea.DockArea.__init__(self, *args, **kwargs)
        self.insert_location = 'bottom'
        self.last_dock = None

    def add_dock_auto_location(self, dock):
        if self.insert_location == 'right':
            self.addDock(dock, self.insert_location, self.last_dock)
        else:
            self.addDock(dock, self.insert_location)
        self.insert_location = {'bottom':'right', 'right':'bottom'}[self.insert_location]
        self.last_dock = dock

class NodeEditWidget(Qt.QFrame):
    def __init__(self, path, attrs):
        Qt.QFrame.__init__(self)
        self.setFrameStyle(Qt.QFrame.Panel)
        self.path = path
        self.spin_widgets = {}
        self.proxy = None

        self.setLayout(Qt.QVBoxLayout())
        self.layout().addWidget(Qt.QLabel('Editing ' + '/'.join(self.path)))

        self.attr_list = Qt.QTreeWidget()
        self.attr_list.setRootIsDecorated(False)
        self.attr_list.setColumnCount(2)
        self.attr_list.setHeaderLabels(['Name', 'Value', 'Type'])

        for attr, value in attrs.items():
            self.attr_list.addTopLevelItem(Qt.QTreeWidgetItem([attr, str(value), str(type(value))]))

        add_attr_box = Qt.QWidget()
        add_attr_box.setLayout(Qt.QHBoxLayout())
        self.attr_name_edit = Qt.QLineEdit()
        self.attr_value_edit = Qt.QLineEdit()
        self.attr_value_edit.returnPressed.connect(self.add_attribute)
        self.attr_list.itemClicked.connect(self.attr_clicked)
        self.add_attr_button = Qt.QPushButton('Add Attribute')
        self.add_attr_button = Qt.QPushButton('Add Attribute')
        self.add_attr_button.clicked.connect(self.add_attribute)
        add_attr_box.layout().addWidget(Qt.QLabel('name'))
        add_attr_box.layout().addWidget(self.attr_name_edit)
        add_attr_box.layout().addWidget(Qt.QLabel('value'))
        add_attr_box.layout().addWidget(self.attr_value_edit)
        add_attr_box.layout().addWidget(self.add_attr_button)

        self.new_attr = True
        self.attr_name_edit.textChanged.connect(self.check_attr_name)
        self.layout().addWidget(self.attr_list)
        self.layout().addWidget(add_attr_box)

        self.attr_list_items = {}

    def set_proxy(self, proxy):
        self.proxy = proxy

    def update(self, attrs):
        for k, v in attrs.items():
            if k not in self.attr_list_items:
                item = Qt.QTreeWidgetItem([k, str(v), str(type(v))])
                self.attr_list_items[k] = item
                self.attr_list.addTopLevelItem(item)
            else:
                self.attr_list_items[k].setText(1, str(v))
                self.attr_list_items[k].setText(2, str(type(v)))

    def check_attr_name(self, name):
        print self.attr_list.findItems("", Qt.Qt.MatchContains)
        if any(i.text(0) == name for i in self.attr_list.findItems("", Qt.Qt.MatchContains)):
            if self.new_attr:
                self.new_attr = False
                self.add_attr_button.setText('Update Attribute')
        else:
            if not self.new_attr:
                self.new_attr = True
                self.add_attr_button.setText('Add Attribute')


    def attr_clicked(self, item):
        self.attr_name_edit.setText(item.text(0))
        self.attr_value_edit.setText(item.text(1))

    def add_attribute(self):
        name = str(self.attr_name_edit.text())
        value = str(self.attr_value_edit.text())
        if value.lower() in ('true', 'false'):
            if value.lower() == 'false':
                value = False
            else:
                value = True
        else:
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass

        if self.proxy is not None:
            self.proxy.set_attrs(**{name:value})
        else:
            if self.new_attr:
                self.attr_list.addTopLevelItem(Qt.QTreeWidgetItem([name, str(value), str(type(value))]))
            else:
                i = self.attr_list.findItems(name, Qt.Qt.MatchExactly, 0)[0]
                i.setText(1, str(value))
            self.attr_name_edit.setText("")
            self.attr_value_edit.setText("")
            return name, value


class LeafEditWidget(NodeEditWidget):
    param_attrs = ['x0', 'y0', 'xscale', 'yscale', 'xlabel', 'ylabel', 'zlabel', 'parametric']
    def __init__(self, path, attrs):
        NodeEditWidget.__init__(self, path, attrs)
        self.params_box = Qt.QWidget()
        self.params_box.setLayout(Qt.QGridLayout())
        for i, name in enumerate(self.param_attrs):
            row, column = int(i / 4), i % 4
            button = Qt.QPushButton(name)
            # Gah, lexical scoping!
            button.clicked.connect((lambda n: (lambda: self.attr_name_edit.setText(n)))(name))
            self.params_box.layout().addWidget(button, row, column)
        self.layout().addWidget(self.params_box)
        #self.rank = leaf.rank

    def add_attribute(self):
        name, value = NodeEditWidget.add_attribute(self)
        if name in self.param_attrs:
            self.background_client.set_params(self.path, self.rank, **{name:value})
    # def __init__(self, leaf):
    #     self.rank = leaf.rank
    #     self.range_area = Qt.QWidget()
    #     self.range_area.setLayout(Qt.QHBoxLayout())
    #     self.layout().addWidget(self.range_area)
    #     self.add_spin('x0', leaf)
    #     self.add_spin('xscale', leaf)
    #     if leaf.rank > 1:
    #         self.add_spin('y0', leaf)
    #         self.add_spin('yscale', leaf)
    #     self.label_area = Qt.QWidget()
    #     self.label_area.setLayout(Qt.QHBoxLayout())
    #     self.layout().addWidget(self.label_area)
    #     self.add_edit('xlabel', leaf)
    #     self.add_edit('ylabel', leaf)
    #     if leaf.rank > 1:
    #         self.add_edit('zlabel', leaf)
    #     self.commit_button = Qt.QPushButton('Commit')
    #     self.commit_button.clicked.connect(self.commit_params)
    #     self.layout().addWidget(self.commit_button)
    #     self.add_attr_widget(leaf)

    # def add_spin(self, name, leaf):
    #     self.range_area.layout().addWidget(Qt.QLabel(name))
    #     widget = pyqtgraph.SpinBox(value=getattr(leaf, name))
    #     self.spin_widgets[name] = widget
    #     self.range_area.layout().addWidget(widget)

    # def add_edit(self, name, leaf):
    #     self.label_area.layout().addWidget(Qt.QLabel(name))
    #     widget = Qt.QLineEdit(getattr(leaf, name))
    #     self.text_widgets[name] = widget
    #     self.label_area.layout().addWidget(widget)

    # def commit_params(self):
    #     params = self.to_dict()
    #     self.background_client.set_params(self.path, self.rank, **params)

    # def to_dict(self):
    #     params = {name: spin.value() for name, spin in self.spin_widgets.items()}
    #     params.update({name: edit.text() for name, edit in self.text_widgets.items()})
    #     return params

class ItemWidget(pyqtgraph.dockarea.Dock):
    dock_area = None
    def __init__(self, ident, **kwargs):
        if len(ident) > 25:
            name = '... ' + ident.split('/')[-1]
        else:
            name = ident
        pyqtgraph.dockarea.Dock.__init__(self, name)
        self.label.setFont(Qt.QFont('Helvetica', pointSize=14))
        self.ident = ident
        self.add_plot_widget(**kwargs)
        self.buttons_widget = Qt.QWidget() #QHBoxWidget()
        self.buttons_widget.setLayout(Qt.QHBoxLayout())
        self.remove_button = Qt.QPushButton('Hide')
        self.remove_button.clicked.connect(self.toggle_hide)
        self.clear_button = Qt.QPushButton('Clear') # Connected to manager action
        self.update_toggle = Qt.QCheckBox('Update')
        self.update_toggle.setChecked(True)
        #self.autoscale_toggle = Qt.QCheckBox('AutoScale')
        #self.autoscale_toggle.setChecked(True)
        self.buttons_widget.layout().addWidget(self.remove_button)
        self.buttons_widget.layout().addWidget(self.clear_button)
        self.buttons_widget.layout().addWidget(self.update_toggle)
        #self.buttons_widget.layout().addWidget(self.autoscale_toggle)
        self.addWidget(self.buttons_widget)
        self.dock_area.add_dock_auto_location(self)

    def is_visible(self):
        return self.parent() is not None

    def toggle_hide(self):
        if self.is_visible():
            self.setParent(None)
            self.label.setParent(None)
            self.visible = False
        else:
            self.dock_area.add_dock_auto_location(self)
            self.visible = True

    def update_params(self, **kwargs):
        self.__dict__.update(kwargs)


    def add_plot_widget(self, **kwargs):
        raise NotImplementedError

    def update(self, data, attrs=None):
        raise NotImplementedError

    def clear_plot(self):
        raise NotImplementedError


class Rank1ItemWidget(ItemWidget):
    rank = 1
    plot_attrs = ["x0", "xscale",
                  "xlabel", "ylabel",
                  "parametric", "plot_args"]
    def __init__(self, ident, **kwargs):
        ItemWidget.__init__(self, ident, **kwargs)

    def add_plot_widget(self, **kwargs):
        #self.line_plt = pyqtgraph.PlotWidget(title=self.ident, **kwargs)
        self.line_plt = pyqtgraph.PlotWidget(**kwargs)
        self.addWidget(self.line_plt)
        self.curve = None

    def update(self, data, attrs=None):
        if attrs is None:
            attrs = {}

        x0 = attrs.get("x0", 0)
        xscale = attrs.get("xscale", 1)
        xlabel = attrs.get("xlabel", "X")
        ylabel = attrs.get("ylabel", "Y")
        parametric = attrs.get("parametric", False)
        plot_args = attrs.get("plot_args", {})


        if data is None or data.shape[0] is 0:
            self.clear_plot()
            return

        if self.update_toggle.isChecked():
            if parametric:
                if data.shape[0] == 2:
                    xdata, ydata = data
                elif data.shape[1] == 2:
                    xdata, ydata = data.T
                else:
                    raise ValueError('data claims to be parametric, but shape is ' + str(data.shape))
            else:
                ydata = data
                xdata = np.arange(x0, x0+(xscale*len(ydata)), xscale)

        self.line_plt.plotItem.setLabels(bottom=(xlabel,), left=(ylabel,))

        if self.curve is None:
            self.curve = self.line_plt.plot(xdata, ydata, **plot_args)
        else:
            self.curve.setData(x=xdata, y=ydata, **plot_args)


class MultiplotItemWidget(Rank1ItemWidget):
    def add_plot_widget(self, **kwargs):
        Rank1ItemWidget.add_plot_widget(self, **kwargs)
        self.curves = defaultdict(lambda: self.line_plt.plot([], pen=tuple(helpers.random_color())))

    def update(self, path, data, attrs=None):
        self.curve = self.curves[path]
        Rank1ItemWidget.update_plot(self, data, attrs)


class ParametricItemWidget(Rank1ItemWidget):
    def __init__(self, path1, path2, **kwargs):
        Rank1ItemWidget.__init__(self, path1[-1]+' vs '+path2[-1], **kwargs)
        self.transpose_toggle = Qt.QCheckBox('Transpose')
        self.transpose_toggle.stateChanged.connect(lambda s: self.update_plot())
        self.buttons_widget.layout().addWidget(self.transpose_toggle)
        self.combined_leaf = DataTreeLeaf(np.array([[]]), 1, parametric=True)
        self.leaf1_data, self.leaf2_data = [], []
        self.path1, self.path2 = path1, path2

    def update_plot(self, path=None, leaf=None):
        if path is None:
            self.combined_leaf.data = np.array(zip(self.leaf1_data, self.leaf2_data))
        elif path == self.path1:
            self.leaf1_data = leaf.data
            self.combined_leaf.data = np.array(zip(leaf.data, self.leaf2_data))
            self.combined_leaf.xlabel = leaf.path[-1]
        elif path == self.path2:
            self.leaf2_data = leaf.data
            self.combined_leaf.data = np.array(zip(self.leaf1_data, leaf.data))
            self.combined_leaf.ylabel = leaf.path[-1]
        else:
            raise ValueError(str(path) + ' is not either ' + str(self.path1) + ' or ' + str(self.path2))
        if self.transpose_toggle.isChecked():
            leaf = copy(self.combined_leaf)
            leaf.data = np.array((leaf.data[:,1], leaf.data[:,0]))
            leaf.xlabel, leaf.ylabel = leaf.ylabel, leaf.xlabel
        else:
            leaf = self.combined_leaf
        Rank1ItemWidget.update_plot(self, leaf, refresh_labels=True)

class Rank2ItemWidget(Rank1ItemWidget):
    rank = 2
    plot_attrs = ["x0", "xscale",
                  "y0", "yscale",
                  "xlabel", "ylabel", "zlabel",
                  "parametric", "plot_args"]
    def __init__(self, ident, **kwargs):
        Rank1ItemWidget.__init__(self, ident, **kwargs)

        self.histogram_check = Qt.QCheckBox('Histogram')
        self.histogram_check.stateChanged.connect(self.img_view.set_histogram)
        self.recent_button = Qt.QPushButton('Most Recent Trace')
        self.recent_button.clicked.connect(self.show_recent)
        self.accum_button = Qt.QPushButton('Accumulated Traces')
        self.accum_button.clicked.connect(self.show_accumulated)
        self.accum_button.hide()
        self.buttons_widget.layout().addWidget(self.histogram_check)
        self.buttons_widget.layout().addWidget(self.recent_button)
        self.buttons_widget.layout().addWidget(self.accum_button)

    def add_plot_widget(self, **kwargs):
        Rank1ItemWidget.add_plot_widget(self)
        self.line_plt.hide() # By default, start out with accum view

        # plt/view explanation here
        # https://groups.google.com/d/msg/pyqtgraph/ccrYl1yyasw/fD9tLrco1PYJ
        # TODO: Identify and separate 1d kwargs and 2d kwargs
        #self.img_plt = pyqtgraph.PlotItem(title=self.ident)
        #self.img_view = pyqtgraph.ImageView(view=self.img_plt)
        self.img_view = CrossSectionWidget()
        self.addWidget(self.img_view)

        #self.line_plt = pyqtgraph.PlotWidget(parent=self, title=self.ident)
        self.addWidget(self.line_plt)
        self.curve = None

    def update(self, data, attrs=None):
        if attrs is None:
            attrs = {}

        x0 = attrs.get("x0", 0)
        y0 = attrs.get("y0", 0)
        xscale = attrs.get("xscale", 1)
        yscale = attrs.get("yscale", 1)
        xlabel = attrs.get("xlabel", "X")
        ylabel = attrs.get("ylabel", "Y")
        zlabel = attrs.get("zlabel", "Z")
        plot_args = attrs.get("plot_args", {})

        if data is None:
            self.clear_plot()
            return

        #if show_most_recent is not None:
        #    if show_most_recent:
        #        self.show_recent()
        #    else:
        #        self.show_accumulated()

        if self.update_toggle.isChecked():
            self.img_view.setLabels(xlabel, ylabel, zlabel)
            Rank1ItemWidget.update(self, data[-1,:], attrs)

            # self.img_view.imageItem.show()
            # Well, this is a hack. I'm not sure why autorange is disabled after setImage
            autorange = self.img_view.getView().vb.autoRangeEnabled()[0]
            self.img_view.setImage(data, autoRange=autorange, pos=[x0, y0], scale=[xscale, yscale])
            self.img_view.getView().vb.enableAutoRange(enable=autorange)

            if data.shape[0] == 1:
                self.show_recent()

    def clear_plot(self):
        Rank1ItemWidget.clear_plot(self)
        #Rank1ItemWidget.update_plot(self, None)
        #self.img_view.setImage(np.array([[]]))
        self.img_view.imageItem.hide()

    def show_recent(self):
        self.img_view.hide()
        self.line_plt.show()
        self.recent_button.hide()
        self.accum_button.show()

    def show_accumulated(self):
        self.img_view.show()
        self.line_plt.hide()
        self.recent_button.show()
        self.accum_button.hide()

def RankNItemWidget(rank, path, **kwargs):
    if rank == 1:
        return Rank1ItemWidget('/'.join(path), **kwargs)
    elif rank == 2:
        return Rank2ItemWidget('/'.join(path), **kwargs)
    else:
        raise Exception('No rank ' + str(rank) + ' item widget')

class CrossSectionWidget(pg.ImageView):
    def __init__(self, trace_size=80, **kwargs):
        view = pg.PlotItem(labels=kwargs.pop('labels', None))
        self.trace_size = trace_size
        pg.ImageView.__init__(self, view=view, **kwargs)
        view.setAspectLocked(lock=False)
        self.cs_layout = pg.GraphicsLayout()
        self.cs_layout.addItem(view, row=1, col=0)
        self.ui.graphicsView.setCentralItem(self.cs_layout)
        self.cross_section_enabled = False
        self.add_cross_section()
        self.hide_cross_section()
        self.search_mode = False
        self.signals_connected = False
        self.set_histogram(False)
        self.ui.histogram.gradient.loadPreset('thermal')
        try:
            self.connect_signal()
        except RuntimeError:
            warnings.warn('Scene not set up, cross section signals not connected')

    def setLabels(self, xlabel="X", ylabel="Y", zlabel="Z"):
        self.view.setLabels(bottom=(xlabel,), left=(ylabel,))
        self.ui.histogram.item.axis.setLabel(text=zlabel)

    def setImage(self, *args, **kwargs):
        pg.ImageView.setImage(self, *args, **kwargs)
        self.update_cross_section()

    def toggle_cross_section(self):
        if self.cross_section_enabled:
            self.hide_cross_section()
        else:
            self.add_cross_section()

    def set_histogram(self, visible):
        self.ui.histogram.setVisible(visible)
        self.ui.roiBtn.setVisible(visible)
        self.ui.normBtn.setVisible(visible)

    def add_cross_section(self):
        self.h_cross_section_item = self.cs_layout.addPlot(row=0, col=0)
        self.v_cross_section_item = self.cs_layout.addPlot(row=1, col=1)
        self.h_cross_section = self.h_cross_section_item.plot([])
        self.v_cross_section = self.v_cross_section_item.plot([])
        self.cs_layout.layout.setRowMaximumHeight(0, self.trace_size)
        self.cs_layout.layout.setColumnMaximumWidth(1, self.trace_size+20)
        self.h_line = pg.InfiniteLine(angle=0, movable=False)
        self.v_line = pg.InfiniteLine(angle=90, movable=False)
        self.view.addItem(self.h_line, ignoreBounds=False)
        self.view.addItem(self.v_line, ignoreBounds=False)
        self.x_cross_index = 0
        self.y_cross_index = 0
        self.cross_section_enabled = True

    def hide_cross_section(self):
        self.cs_layout.layout.removeItem(self.h_cross_section_item)
        self.cs_layout.layout.removeItem(self.v_cross_section_item)
        self.h_cross_section_item.close()
        self.v_cross_section_item.close()
        self.view.removeItem(self.h_line)
        self.view.removeItem(self.v_line)
        self.cross_section_enabled = False

    def connect_signal(self):
        """This can only be run after the item has been embedded in a scene"""
        if self.signals_connected:
            warnings.warn("")
        if self.imageItem.scene() is None:
            raise RuntimeError('Signal can only be connected after it has been embedded in a scene.')
        self.imageItem.scene().sigMouseClicked.connect(self.toggle_search)
        self.imageItem.scene().sigMouseMoved.connect(self.handle_mouse_move)
        self.timeLine.sigPositionChanged.connect(self.update_cross_section)
        self.signals_connected = True

    def toggle_search(self, mouse_event):
        if mouse_event.double():
            self.toggle_cross_section()
        else:
            self.search_mode = not self.search_mode
            if self.search_mode:
                self.handle_mouse_move(mouse_event.scenePos())

    def handle_mouse_move(self, mouse_event):
        if self.cross_section_enabled and self.search_mode:
            view_coords = self.imageItem.getViewBox().mapSceneToView(mouse_event)
            view_x, view_y = view_coords.x(), view_coords.y()
            item_coords = self.imageItem.mapFromScene(mouse_event)
            item_x, item_y = item_coords.x(), item_coords.y()
            max_x, max_y = self.imageItem.image.shape
            if item_x < 0 or item_x > max_x or item_y < 0 or item_y > max_y:
                return
            self.v_line.setPos(view_x)
            self.h_line.setPos(view_y)
            #(min_view_x, max_view_x), (min_view_y, max_view_y) = self.imageItem.getViewBox().viewRange()
            #idx_x = helpers.linterp(view_coords.x(), min_view_x, max_view_x, 0, max_x)
            #idx_y = helpers.linterp(view_coords.y(), min_view_y, max_view_y, 0, max_y)
            #print view_coords.x(), min_view_x, max_view_x, max_x, idx_x
            self.x_cross_index = max(min(int(item_x), max_x-1), 0)
            self.y_cross_index = max(min(int(item_y), max_y-1), 0)
            self.update_cross_section()

    def update_cross_section(self):
        self.h_cross_section.setData(self.imageItem.image[:, self.y_cross_index])
        self.v_cross_section.setData(self.imageItem.image[self.x_cross_index, :], range(self.imageItem.image.shape[1]))