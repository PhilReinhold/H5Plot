from collections import defaultdict
from copy import copy
import warnings

from PyQt4 import Qt
import pyqtgraph
import pyqtgraph as pg
import pyqtgraph.dockarea
import numpy as np

import helpers
from model import DataTreeLeaf

class DataTreeLeafItem(Qt.QTreeWidgetItem):
    @property
    def path(self):
        if self.parent() is None:
            return (str(self.text(0)),)
        else:
            return self.parent().path + (str(self.text(0)),)

    @property
    def strpath(self):
        return '/'.join(map(str, self.path))


Qt.QTreeWidgetItem.is_leaf = lambda item: str(item.text(1)) != ""
Qt.QTreeWidgetItem.getChildren = lambda item: [item.child(i) for i in range(item.childCount())]

class MyDockArea(pyqtgraph.dockarea.DockArea):
    def __init__(self, *args, **kwargs):
        pyqtgraph.dockarea.DockArea.__init__(self, *args, **kwargs)
        self.insert_location = 'bottom'

    def add_dock_auto_location(self, dock):
        self.addDock(dock, self.insert_location)
        self.insert_location = {'bottom':'right', 'right':'bottom'}[self.insert_location]

class LeafEditWidget(Qt.QFrame):
    def __init__(self, leaf):
        Qt.QFrame.__init__(self)
        self.setFrameStyle(Qt.QFrame.Panel)
        self.path = leaf.path
        self.spin_widgets = {}
        self.text_widgets = {}

        self.setLayout(Qt.QVBoxLayout())
        self.layout().addWidget(Qt.QLabel('Editing ' + '/'.join(self.path)))
        self.range_area = Qt.QWidget()
        self.range_area.setLayout(Qt.QHBoxLayout())
        self.layout().addWidget(self.range_area)
        self.add_spin('x0', leaf)
        self.add_spin('xscale', leaf)
        if leaf.rank > 1:
            self.add_spin('y0', leaf)
            self.add_spin('yscale', leaf)
        self.label_area = Qt.QWidget()
        self.label_area.setLayout(Qt.QHBoxLayout())
        self.layout().addWidget(self.label_area)
        self.add_edit('xlabel', leaf)
        self.add_edit('ylabel', leaf)
        if leaf.rank > 1:
            self.add_edit('zlabel', leaf)
        self.commit_button = Qt.QPushButton('Commit')
        self.layout().addWidget(self.commit_button)

    def add_spin(self, name, leaf):
        self.range_area.layout().addWidget(Qt.QLabel(name))
        widget = pyqtgraph.SpinBox(value=getattr(leaf, name))
        self.spin_widgets[name] = widget
        self.range_area.layout().addWidget(widget)

    def add_edit(self, name, leaf):
        self.label_area.layout().addWidget(Qt.QLabel(name))
        widget = Qt.QLineEdit(getattr(leaf, name))
        self.text_widgets[name] = widget
        self.label_area.layout().addWidget(widget)

    def to_dict(self):
        params = {name: spin.value() for name, spin in self.spin_widgets.items()}
        params.update({name: edit.text() for name, edit in self.text_widgets.items()})
        return params

class ItemWidget(pyqtgraph.dockarea.Dock):
    def __init__(self, ident, dock_area, **kwargs):
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
        self.dock_area = dock_area
        self.dock_area.add_dock_auto_location(self)
        self.visible = True

    def update_params(self, **kwargs):
        self.__dict__.update(kwargs)

    def toggle_hide(self):
        #self.setVisible(not(self.isVisible()))
        if self.visible:
            self.setParent(None)
            self.label.setParent(None)
            self.visible = False
        else:
            self.dock_area.add_dock_auto_location(self)
            self.visible = True

    def add_plot_widget(self, **kwargs):
        raise NotImplementedError

    def update_plot(self, leaf):
        raise NotImplementedError

    def clear_plot(self):
        raise NotImplementedError


class Rank1ItemWidget(ItemWidget):
    def __init__(self, ident, dock_area, **kwargs):
        ItemWidget.__init__(self, ident, dock_area, **kwargs)
        self.rank = 1

    def add_plot_widget(self, **kwargs):
        #self.line_plt = pyqtgraph.PlotWidget(title=self.ident, **kwargs)
        self.line_plt = pyqtgraph.PlotWidget(**kwargs)
        self.addWidget(self.line_plt)
        self.curve = None

    def update_plot(self, leaf, refresh_labels=False, **kwargs):
        if leaf is None or leaf.data is None or leaf.data.shape[0] is 0:
            self.clear_plot()
            return

        if self.update_toggle.isChecked():
            if leaf.parametric:
                if leaf.data.shape[0] == 2:
                    xdata, ydata = leaf.data
                elif leaf.data.shape[1] == 2:
                    xdata, ydata = leaf.data.T
                else:
                    raise ValueError('Leaf claims to be parametric, but shape is ' + str(leaf.data.shape))
            else:
                ydata = leaf.data
                xdata = np.arange(leaf.x0, leaf.x0+(leaf.xscale*len(ydata)), leaf.xscale)

        if refresh_labels:
            self.line_plt.plotItem.setLabels(bottom=(leaf.xlabel,), left=(leaf.ylabel,))

        if self.curve is None:
            self.curve = self.line_plt.plot(xdata, ydata, **kwargs)
        else:
            self.curve.setData(x=xdata, y=ydata, **kwargs)

    def clear_plot(self):
        if self.curve is not None:
            self.line_plt.removeItem(self.curve)
            self.curve = None


class MultiplotItemWidget(Rank1ItemWidget):
    def add_plot_widget(self, **kwargs):
        Rank1ItemWidget.add_plot_widget(self, **kwargs)
        self.curves = defaultdict(lambda: self.line_plt.plot([], pen=tuple(helpers.random_color())))

    def update_plot(self, path, leaf):
        self.curve = self.curves[path]
        Rank1ItemWidget.update_plot(self, leaf)


class ParametricItemWidget(Rank1ItemWidget):
    def __init__(self, path1, path2, dock_area, **kwargs):
        Rank1ItemWidget.__init__(self, path1[-1]+' vs '+path2[-1], dock_area, **kwargs)
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
    def __init__(self, ident, dock_area, **kwargs):
        Rank1ItemWidget.__init__(self, ident, dock_area, **kwargs)
        self.rank = 2

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

    def update_plot(self, leaf, refresh_labels=False, show_most_recent=None):
        if leaf is None or leaf.data is None:
            self.clear_plot()
            return

        if show_most_recent is not None:
            if show_most_recent:
                self.show_recent()
            else:
                self.show_accumulated()
        if self.update_toggle.isChecked():
            if refresh_labels:
                self.img_view.setLabels(leaf.xlabel, leaf.ylabel, leaf.zlabel)
            Rank1ItemWidget.update_plot(self, leaf.to_rank1())
            self.img_view.imageItem.show()
            self.img_view.setImage(leaf.data, pos=[leaf.x0, leaf.y0], scale=[leaf.xscale, leaf.yscale])
            if leaf.data.shape[0] == 1:
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
            self.h_line.setPos(view_coords.y())
            self.v_line.setPos(view_coords.x())
            max_x, max_y = self.imageItem.image.shape
            self.x_cross_index = max(min(int(view_coords.x()), max_x-1), 0)
            self.y_cross_index = max(min(int(view_coords.y()), max_y-1), 0)
            self.update_cross_section()

    def update_cross_section(self):
        self.h_cross_section.setData(self.imageItem.image[:, self.y_cross_index])
        self.v_cross_section.setData(self.imageItem.image[self.x_cross_index, :], range(self.imageItem.image.shape[1]))