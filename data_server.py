import zmq
import numpy as np
import h5py


def send_array(socket, A, flags=0, copy=True, track=False):
    md = dict(
        dtype = str(A.dtype),
        shape = A.shape,
    )
    socket.send_json(md, flags|zmq.SNDMORE)
    return socket.send(A, flags, copy=copy, track=track)


def recv_array(socket, flags=0, copy=True, track=False):
    md = socket.recv_json(flags=flags)
    msg = socket.recv(flags=flags, copy=copy, track=track)
    buf = buffer(msg)
    A = np.frombuffer(buf, dtype=md['dtype'])
    return A.reshape(md['shape'])

class DataCommands:
    set = 0
    setslice = 1
    append = 2
    attr = 3
    load = 4


class DataServer:
    def __init__(self):
        ctx = zmq.Context()
        self.sub_socket = ctx.socket(zmq.SUB)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, '')
        self.sub_socket.bind('tcp://127.0.0.1:7676')
        self.pub_socket = ctx.socket(zmq.PUB)
        self.sub_socket.bind('tcp://127.0.0.1:7677')
        #self.rep_socket = ctx.socket(zmq.REP)
        #self.rep_socket.bind('tcp://127.0.0.1:7678')

        self.open_files = {}
        self.running = True

    def main_loop(self):
        while self.running:
            if self.sub_socket.poll():
                json = self.sub_socket.recv_json()
                command, path = json['command'], json['path']

                if self.sub_socket.getsockopt(zmq.RCVMORE):
                    data = recv_array(self.sub_socket)
                else:
                    data = json['data']

                if command == DataCommands.load:
                    file = self.get_or_make_path(path)
                    self.publish_file(path, file)

                group = self.get_or_make_path(path[:-1])
                dsetname = path[-1]

                if command == DataCommands.set:
                    print 'set', group, path, data
                    group[dsetname] = data
                elif command == DataCommands.setslice:
                    slice = json['extra']
                    group[dsetname][slice] = data
                elif command == DataCommands.append:
                    #dataset.append_data(data)
                    raise NotImplementedError
                elif command == DataCommands.attr:
                    name, value = data
                    group[dsetname].attrs[name] = value

                group[dsetname].file.flush()
                self.publish_array(path, np.array(group[dsetname]))

    def publish_array(self, path, array):
        self.pub_socket.send_json({'path': path}, flags=zmq.SNDMORE)
        send_array(self.pub_socket, array)

    def publish_attrs(self, path, attrs):
        pass

    def publish_file(self, path, file):
        def rec_load_file(lastpath, group):
            for name, dset in group.items():
                thispath = lastpath + (name,)
                if dset.attrs:
                    self.publish_attrs(thispath, dset.attrs)
                if isinstance(dset, h5py.Dataset):
                    self.publish_array(lastpath + (name,), np.array(dset))
                else:
                    rec_load_file(thispath, dset)
        rec_load_file(path, file)



    def get_or_make_path(self, path, as_group=True, open_file=True):
        if open_file and path[0] not in self.open_files:
            self.open_files[path[0]] = h5py.File(path[0])

        current = self.open_files

        for i, p in enumerate(path):
            if p not in current:
                if i == (len(path)-1) and not as_group:
                    current.create_dataset(p)
                current.create_group(p)
            current = current[p]
        return current

    def resolve_path(self, path):
        file = self.open_files
        for pathitem in path:
            file = file[pathitem]
        return file


class DataServerClient:
    def __init__(self, socket=None):
        if socket is None:
            ctx = zmq.Context()
            self.pub_socket = ctx.socket(zmq.PUB)
            self.pub_socket.connect('tcp://127.0.0.1:7676')
        else:
            self.pub_socket = socket
        self.path = ()

    def _clone(self):
        c = DataServerClient(self.pub_socket)
        c.path = self.path
        return c

    def __getitem__(self, item):
        assert isinstance(item, str), "Item must be name of data group, not " + str(item)
        c = self._clone()
        c.path += (item,)
        return c

    def __setitem__(self, key, data):
        if isinstance(key, (int, tuple, slice)):
            self._send(DataCommands.setslice, self.path, data, extra=key)
        else:
            self._send(DataCommands.set, self.path + (key,), data)

    def _send(self, command, path, data, extra=None):
        json = {'command': command, 'path': path}
        if extra is not None:
            json['extra'] = extra

        if isinstance(data, list):
            data = np.array(data)

        if isinstance(data, np.ndarray):
            self.pub_socket.send_json(json, flags=zmq.SNDMORE)
            send_array(self.pub_socket, data)
        else:
            json['data'] = data
            self.pub_socket.send_json(json)

    def append_data(self, data):
        self._send(DataCommands.append, self.path, data)


