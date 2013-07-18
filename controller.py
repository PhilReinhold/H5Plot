import time

from PyQt4 import Qt
import h5py
import Pyro4
import numpy as np
import zmq

from model import DataTree, DataTreeLeaf, DataTreeLeafReduced
import helpers
import config

#Pyro4.config.COMMTIMEOUT = 3.5
#Pyro4.config.DOTTEDNAMES = True
Pyro4.config.SERVERTYPE = 'multiplex'
Pyro4.config.ONEWAY_THREADED = True
RUNNING = True

class DataManager(Qt.QObject):
    def __init__(self, path_delim='/'):
        Qt.QObject.__init__(self)
        self.data = None
        self.delim = path_delim
        self.coverage = False
        self.gui = None
        self.params = {}
        self.zmq_ctx = zmq.Context()
        self.data_conns = {}

    def connect_zmq(self, addr):
        sock = self.zmq_ctx.socket(zmq.SUB)
        sock.connect(addr)
        sock.setsockopt(zmq.SUBSCRIBE, '')
        self.data_conns[addr] = sock

    def receive_data(self, addr, dtype, shape, mode, path, slice=None):
        if self.data_conns[addr].poll(timeout=1000):
            data = self.data_conns[addr].recv(copy=False, track=False)
        else:
            raise EnvironmentError('Unable to receive data over socket ' + repr(self.data_conns[addr]))
        arr = np.frombuffer(buffer(data), dtype)
        arr.resize(shape)
        if mode == 'append':
            self.append_data(path, arr)
        elif mode == 'set':
            self.set_data(path, arr, slice=slice)
        else:
            raise ValueError('invalid mode: ' + repr(mode))

    def set_param(self, name, value):
        self.params[name] = value

    def _connect_data(self):
        self.data = DataTree(self.gui)

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

    def set_data(self, name_or_path, data, slice=None, parametric=False, **initargs):
        path = helpers.canonicalize_path(name_or_path)
        if parametric and isinstance(data, (np.ndarray, list)):
            data = np.array(data)
            if data.shape[1] == 2:
                data = np.transpose(data)

        if parametric or isinstance(data, tuple):
            parametric = True
            rank = len(data) - 1
            data = np.array(data)
        else:
            data = np.array(data)
            rank = len(data.shape)

        data_tree_args, plot_args, curve_args = helpers.separate_init_args(initargs)
        data_tree_args['parametric'] = parametric

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

    def append_data(self, name_or_path, data, show_most_recent=None, parametric=False, **initargs):
        path = helpers.canonicalize_path(name_or_path)

        if parametric or isinstance(data, tuple):
            parametric = True
            rank = len(data) - 1
            data = np.array(data)
        else:
            data = np.array(data)
            rank = len(data.shape) + 1

        data_tree_args, plot_args, curve_args = helpers.separate_init_args(initargs)
        data_tree_args['parametric'] = parametric
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

    def update_plot(self, name_or_path, refresh_labels=False, show_most_recent=None, **curve_args):
        path = helpers.canonicalize_path(name_or_path)
        item = self.data.resolve_path(path)
        tree_widget = self.gui.tree_widgets[path]
        try:
            tree_widget.setText(1, str(item.data.shape))
        except AttributeError:
            tree_widget.setText(1, 'No Data')
        tree_widget.setText(2, str(item.save))
        tree_widget.setText(3, str(item.plot))
        if item.plot:
            self.gui.plot_widgets_update_log[path] = time.time()
            if item.rank == 2:
                self.gui.plot_widgets[path].update_plot(item,
                        refresh_labels=refresh_labels, show_most_recent=show_most_recent, **curve_args)
            else:
                self.gui.plot_widgets[path].update_plot(item, refresh_labels=refresh_labels, **curve_args)
        self.gui.update_multiplots(path, item)

    def remove_item(self, name_or_path):
        print 'background.remove_item', name_or_path
        path = helpers.canonicalize_path(name_or_path)
        item = self.data.resolve_path(path)
        if isinstance(item, DataTreeLeaf):
            name = path[-1]
            group_path = path[:-1]
            group = self.data.resolve_path(group_path)
            del group[name]
            self.gui.remove_item(path)
            while group_path and len(group.keys()) == 0:
                name = group_path[-1]
                group_path = group_path[:-1]
                group = self.data.resolve_path(group_path)
                del group[name]
                self.gui.remove_item(group_path + (name,))
        else:
            for name in item.keys():
                self.remove_item(path + (name,))

    def save_all(self): # TODO
        raise NotImplementedError

    def load_h5file(self, filename, readonly=False):
        mode = 'r' if readonly else 'a'
        f = h5py.File(filename, mode)
        if not readonly:
            self.data[filename] = DataTree(self.gui, filename, file=f)
        else:
            self.data[filename] = DataTree(self.gui, filename, open_file=False)
        try:
            self.rec_load_file(f, (filename,), readonly)
            for k, v in f.attrs.items():
                self.data[filename].attrs[k] = v
        except Exception:
            self.remove_item(filename)
            raise
        if readonly:
            f.close()

    def rec_load_file(self, file, path, readonly):
        for name, ds in file.items():
            this_path = path + (name,)
            self.msg(name, type(ds))
            if isinstance(ds, h5py.Group):
                self.msg('recursing', this_path)
                self.rec_load_file(ds, this_path, readonly)
                self.data.resolve_path(this_path).load_attrs_from_ds(ds)
            else:
                parametric = ds.attrs.get('parametric', False)
                if 0 in ds.shape: # Length 0 arrays are buggy in h5py...
                    self.msg('Length 0 array %s ignored' % '/'.join(this_path))
                    continue
                self.msg('set_data', this_path, type(ds), np.array(ds).shape)
                self.set_data(this_path, np.array(ds), save=(not readonly), parametric=parametric)
                self.msg('set_data done', this_path)
                #self.get_or_make_leaf(this_path).load_attrs_from_ds(ds)
                self.data.resolve_path(this_path).load_attrs_from_ds(ds)
                self.update_plot(this_path, refresh_labels=True)

    def clear_data(self, path=None, leaf=None):
        assert path is not None or leaf is not None
        if leaf is None:
            leaf = self.get_or_make_leaf(path)
        else:
            path = leaf.path
        if leaf.rank == 1:
            leaf.data = None
        elif leaf.rank == 2:
            leaf.data = None
        if leaf.plot:
            self.update_plot(path)

    def clear_all_data(self):
        for path, leaf in self.data.leaves():
            self.clear_data(leaf=leaf)

    def serve(self):
        print 'serving'
        if self.coverage:
            from coverage import coverage
            cov = coverage(data_suffix='manager')
            cov.start()
        with Pyro4.Daemon(host=config.manager_host, port=config.manager_port) as d:
            global RUNNING
            self.running = True
            d.register(self, config.manager_id)
            d.requestLoop(lambda: RUNNING)
        print 'done serving'
        self.data.close()
        print "data closed"
        if self.coverage:
            cov.stop()
            cov.save()
        #self.emit(Qt.SIGNAL('server done'))
        print "sig emitted"

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

    def save_as_file(self, path):
        data = self.data.resolve_path(path)
        assert isinstance(data, DataTree)
        assert helpers.valid_h5file(path[-1])
        with h5py.File(path[-1], 'a') as f:
            for item in data.values():
                item.save_in_file(f)

    def save_with_file(self, path, filename):
        with h5py.File(filename, 'a') as h5file:
            data = self.data.resolve_path(path)
            f = h5file
            for p in path[:-1]:
                if p not in f:
                    f = f.create_group(p)
                else:
                    f = f[p]
            data.save_in_file(f)

    def msg(self, *args):
        self.gui.msg(*args)

    def gui_method(self, method, *args, **kwargs):
        getattr(self.gui, method)(*args, **kwargs)

if __name__ == "__main__":
    test_manager = DataManager()
