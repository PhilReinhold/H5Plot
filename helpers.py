import os

import numpy as np
import pyqtgraph

def take_items(d, l):
    res = {}
    for i in l:
        if i in d:
            res[i] = d[i]
    return res

def separate_init_args(initargs):
    data_tree_args = ['rank', 'save', 'plot', 'parametric', 'x0', 'y0',
                      'xscale', 'yscale', 'xlabel', 'ylabel', 'zlabel']
    plot_args = ['title', 'labels', 'name', 'axisItems']
    pen_args = ['color', 'width', 'style', 'cosmetic', 'hsv']
    curve_args = ['pen', 'shadowPen', 'fillLevel', 'fillBrush', 'symbol',
                  'symbolPen', 'symbolBrush', 'symbolSize', 'pxMode', 'antialias', 'decimate', 'name']

    if 'scatter' in initargs:
        if initargs['scatter']:
            initargs['parametric'] = True
            initargs['pen'] = None
            initargs['symbolPen'] = None
            initargs['symbol'] = 't'
        del initargs['scatter']

    pen_dict = take_items(initargs, pen_args)
    if len(pen_dict) > 0 and 'pen' not in initargs:
        initargs['pen'] = pyqtgraph.mkPen(**pen_dict)

    return (take_items(initargs, data_tree_args),
            take_items(initargs, plot_args),
            take_items(initargs, curve_args))

def linterp(x, x0, x1, y0, y1):
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)
