import time

from PyQt4 import Qt
import h5py
import Pyro4
import numpy as np
import zmq

from model import DataTree, DataTreeLeaf, DataTreeLeafReduced
import helpers
import config
from data_server import send_array, recv_array

RUNNING = True

class DataManager(Qt.QObject):
    def __init__(self):
        Qt.QObject.__init__(self)
        self.data = {}
        #self.delim = path_delim
        #self.coverage = False
        self.gui = None

    def get_or_make_leaf(self, path, rank=None, data_tree_args={}, plot_args={}, reduced=False):
        group = self.data.resolve_path(path[:-1])
        if path[-1] not in group:
            if rank is None:
                raise ValueError('Path %s not found and rank not specified' % '/'.join(path))
            if not isinstance(group, DataTree):
                raise RuntimeError('Trying to add name %s to existing dataset %s' % (path[-1], '/'.join(path[:-1])))
            leaf = group.make_child_leaf(path[-1], rank, **data_tree_args)
            if not isinstance(leaf, DataTreeLeaf):
                raise ValueError('path does not store a leaf, but rather a ' + str(type(leaf)))
            self.gui.add_tree_widget(path, data=True, save=leaf.save, plot=leaf.plot)
            self.gui.add_plot_widget(path, rank, **plot_args)
            if not leaf.plot:
                self.gui.toggle_path(path)
                #params = {'x0': leaf.x0, 'xscale': leaf.xscale, 'xlabel': leaf.xlabel, 'ylabel': leaf.ylabel}
                #if rank > 1:
                #    params.update({'y0': leaf.y0, 'yscale': leaf.yscale, 'zlabel': leaf.zlabel})
        else:
            leaf = group[path[-1]]
            if not isinstance(leaf, DataTreeLeaf):
                self.msg(leaf, type(leaf))
                raise ValueError('Path %s exists and is not a leaf' % '/'.join(path))
            if rank is not None and rank != leaf.rank:
                raise ValueError('Rank of existing leaf %s = %d does not match rank given = %d' % ('/'.join(path), leaf.rank, rank))
            assert (rank is None) or (rank == leaf.rank)
            for key, val in data_tree_args.items():
                setattr(leaf, key, val)
            if len(data_tree_args) > 0:
                self.update_plot(path, refresh_labels=True)

        if reduced:
            return DataTreeLeafReduced(leaf)

        return leaf

    def set_params(self, path, rank, **initargs):
        data_tree_args, plot_args, curve_args = helpers.separate_init_args(initargs)
        leaf = self.get_or_make_leaf(path, rank, data_tree_args, plot_args)
        if leaf.file is not None:
            leaf.save_in_file()
        self.update_plot(path, refresh_labels=True, **curve_args)

    def set_data(self, name_or_path, data, slice=None, **initargs):
        path = helpers.canonicalize_path(name_or_path)
        data_tree_args, plot_args, curve_args = helpers.separate_init_args(initargs)
        parametric = data_tree_args.get('parametric', False)

        if parametric and isinstance(data, (np.ndarray, list)):
            data = np.array(data)
            if data.shape[1] == 2:
                data = np.transpose(data)

        if parametric or isinstance(data, tuple):
            data_tree_args['parametric'] = True
            rank = len(data) - 1
            data = np.array(data)
        else:
            data = np.array(data)
            rank = len(data.shape)

        if slice is None:
            leaf = self.get_or_make_leaf(path, rank, data_tree_args, plot_args)
            leaf.data = data
        else:
            leaf = self.get_or_make_leaf(path, None, data_tree_args, plot_args)
            leaf.data[slice] = data

        if leaf.file is not None:
            leaf.save_in_file()
        #if leaf.plot:
        self.update_plot(name_or_path, refresh_labels=(len(initargs) > 0), **curve_args)
        return ()

    def append_data(self, name_or_path, data, show_most_recent=None, **initargs):
        path = helpers.canonicalize_path(name_or_path)
        data_tree_args, plot_args, curve_args = helpers.separate_init_args(initargs)
        parametric = data_tree_args.get('parametric', False)

        if parametric or isinstance(data, tuple):
            parametric = True
            rank = len(data) - 1
            data = np.array(data)
        else:
            data = np.array(data)
            rank = len(data.shape) + 1

        leaf = self.get_or_make_leaf(path, rank, data_tree_args, plot_args)

        if leaf.data is None:
            leaf.data = np.array([data])
        else:
            if rank is 1 and not parametric:
                leaf.data = np.hstack((leaf.data, data))
            else:
                leaf.data = np.vstack((leaf.data, data))

        if leaf.file is not None:
            leaf.save_in_file()
        #if leaf.plot:
        self.update_plot(name_or_path, refresh_labels=(len(initargs) > 0),
                         show_most_recent=show_most_recent, **curve_args)

    def get_data(self, name_or_path, slice=None):
        path = helpers.canonicalize_path(name_or_path)
        item = self.data.resolve_path(path)
        if not isinstance(item, DataTreeLeaf):
            raise ValueError('Leaf not found ' + str(path))
        if slice is not None:
            return np.array(item.data)[slice]
        else:
            return np.array(item.data)

    def set_attr(self, name_or_path, item, value):
        path = helpers.canonicalize_path(name_or_path)
        node = self.data.resolve_path(path)
        node.attrs[item] = value
        if node.file is not None:
            self.msg(node.file, node.path)
            if isinstance(node, DataTreeLeaf):
                node.file[node.path[-1]].attrs[item] = value
            else:
                node.file.attrs[item] = value

    def get_attr(self, name_or_path, item):
        return self.get_all_attrs(name_or_path)[item]

    def get_all_attrs(self, name_or_path):
        path = helpers.canonicalize_path(name_or_path)
        node = self.data.resolve_path(path)
        return node.attrs

    #def update_plot(self, name_or_path, refresh_labels=False, show_most_recent=None, **curve_args):
    #    path = helpers.canonicalize_path(name_or_path)
    #    item = self.data.resolve_path(path)
    #    tree_widget = self.gui.tree_widgets[path]
    #    try:
    #        tree_widget.setText(1, str(item.data.shape))
    #    except AttributeError:
    #        tree_widget.setText(1, 'No Data')
    #    tree_widget.setText(2, str(item.save))
    #    tree_widget.setText(3, str(item.plot))
    #    if item.plot:
    #        self.gui.plot_widgets_update_log[path] = time.time()
    #        if item.rank == 2:
    #            self.gui.plot_widgets[path].update_plot(item,
    #                    refresh_labels=refresh_labels, show_most_recent=show_most_recent, **curve_args)
    #        else:
    #            self.gui.plot_widgets[path].update_plot(item, refresh_labels=refresh_labels, **curve_args)
    #    self.gui.update_multiplots(path, item)

    # Not needed
    #def remove_item(self, path):
    #    del self.data[path]
    #    del self.attrs[path]
    #    self.gui.remove_item(path)

    # Why do we need clear again?
    #def clear_data(self, path=None, leaf=None):
    #    assert path is not None or leaf is not None
    #    if leaf is None:
    #        leaf = self.get_or_make_leaf(path)
    #    else:
    #        path = leaf.path
    #    if leaf.rank == 1:
    #        leaf.data = None
    #    elif leaf.rank == 2:
    #        leaf.data = None
    #    if leaf.plot:
    #        self.update_plot(path)

    #def clear_all_data(self):
    #    for path, leaf in self.data.leaves():
    #        self.clear_data(leaf=leaf)

    def serve(self):
        print 'serving'
        if self.coverage:
            from coverage import coverage
            cov = coverage(data_suffix='manager')
            cov.start()

        listen_socket = self.zmq_ctx.socket(zmq.SUB)
        listen_socket.setsockopt(zmq.SUBSCRIBE, '')
        listen_socket.connect('tcp://127.0.0.1:7677')
        last_winupdate_time = 0
        self.dirty_data = set([])
        self.dirty_attrs = set([])
        global RUNNING
        while RUNNING:
            data_patch = {}
            attrs_patch = {}
            while listen_socket.poll():
                json = listen_socket.recv_json()
                path = json['path']
                if 'attrs' in json:
                    attrs_patch[path] = json['attrs']
                else:
                    data = recv_array(listen_socket)
                    data_patch[path] = data
            self.data.update(data_patch)
            self.dirty_data.update(data_patch.keys())
            self.attrs.update(attrs_patch)
            self.dirty_attrs.update(attrs_patch.keys())
            if time.time() - last_winupdate_time > self.inter_winupdate_time:
                self.winupdate_tree()
                self.winupdate_data()
                self.winupdate_attrs()
                last_winupdate_time = time.time()

        if self.coverage:
            cov.stop()
            cov.save()

    def winupdate_tree(self):
        for key in self.dirty_data.union(self.dirty_attrs):
            if key in self.data:
                shape = self.data[key].shape
                save = self.attrs[key].get('save', True)
                plot = self.attrs[key].get('plot', True)
                self.gui.add_tree_widget(key, shape, save=save, plot=plot)

    def winupdate_data(self):
        for key in self.dirty_data:
            plot_attrs = self.get_plot_attrs(key)
            self.gui.plot_widgets[key].update(self.data[key], plot_attrs)

    def winupdate_attrs(self):
        for key in self.dirty_attrs:
            self.gui.attrs_widgets[key].update(self.attrs[key])

    def get_plot_attrs(self, path):
        attrs = self.attrs[path]
        x0 = attrs.get('x0', 0)
        xscale = attrs.get('xscale', 1)
        y0 = attrs.get('y0', 0)
        yscale = attrs.get('yscale', 1)
        xlabel = attrs.get('xlabel', 'X')
        ylabel = attrs.get('ylabel', 'Y')
        zlabel = attrs.get('zlabel', 'Z')
        parametric = attrs.get('parametric', False)
        plot_args = {} # TODO: Extract Plot Arguments
        return (x0, xscale, y0, yscale, xlabel, ylabel, zlabel, parametric, plot_args)

    def abort_daemon(self):
        global RUNNING
        RUNNING = False
        print 'Aborted!'

    #def wait_for_cleanup_dialog(self):
    #    print 'here'
    #    dialog = Qt.QMessageBox()
    #    dialog.setText("Please wait while the server cleans up...")
    #    self.connect(self, Qt.SIGNAL('server done'), dialog.accept)
    #    #self.background_thread.finished.connect(dialog.accept)
    #    print 'here2'
    #    dialog.exec_()
    #    print 'here3'

    #def save_as_file(self, path):
    #    data = self.data.resolve_path(path)
    #    assert isinstance(data, DataTree)
    #    assert helpers.valid_h5file(path[-1])
    #    with h5py.File(path[-1], 'a') as f:
    #        for item in data.values():
    #            item.save_in_file(f)

    #def save_with_file(self, path, filename):
    #    with h5py.File(filename, 'a') as h5file:
    #        data = self.data.resolve_path(path)
    #        f = h5file
    #        for p in path[:-1]:
    #            if p not in f:
    #                f = f.create_group(p)
    #            else:
    #                f = f[p]
    #        data.save_in_file(f)

    def msg(self, *args):
        self.gui.msg(*args)

    def gui_method(self, method, *args, **kwargs):
        getattr(self.gui, method)(*args, **kwargs)

if __name__ == "__main__":
    test_manager = DataManager()
