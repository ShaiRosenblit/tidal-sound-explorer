import json
import socket
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import cm

from utils import load_df


UDP_IP = "127.0.0.1"
UDP_PORT = 5005
UDP_PORT_plotter2player = 5006
MAX_POINTS_IN_QUEUE = 30  # adjust this number if the event rate is too high and the plot gets out of sync

sock = socket.socket(socket.AF_INET,
                     socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

sock_plotter2player = socket.socket(socket.AF_INET,
                     socket.SOCK_DGRAM)

plt.style.use('dark_background')


class Scope:
    def __init__(self, fig, ax, plot_df, dt, init_random_keys=True):
        print("Get ready for some points!!!")
        plt.rcParams['keymap.xscale'].remove('k')
        plt.rcParams['keymap.save'].remove('s')
        self.fig = fig
        self.ax = ax
        self.dt = dt
        self.df = plot_df
        self.points = np.array([[0, 0, 0, -1]])  # x, y, ,size, last_t
        self.points_colors = np.array(['r'])
        self.t = 0
        self.color_vec = np.array(['b'] * len(plot_df))
        self.size_vec = np.array([1] * len(plot_df))
        self.sc = ax.scatter(plot_df['col_x'], plot_df['col_y'],
                             alpha=0.5, picker=10, c=plot_df.color,
                             s=plot_df.point_size, cmap=cm.get_cmap('tab20'))
        self.default_point_dur = 0.05
        self.default_size_factor = 100
        self.default_color = 'w'
        self.p = self.ax.scatter([0], [0], visible=False)
        self.num_text_elements = 20
        self.texts = [self.ax.text(0, 0, '', color='w') for i in range(self.num_text_elements)]
        self.poiter_clicked = False
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.fig.canvas.mpl_connect('key_press_event', self.on_press)
        self.selected_key = '1'
        self.clicked_key_vals = {}
        if init_random_keys:
            for key in '0123456789':
                self.clicked_key_vals[key] = 0.5+np.random.randn()*0.2, 0.5+np.random.randn()*0.2
        sock_plotter2player.sendto(json.dumps(self.clicked_key_vals).encode('utf-8'), (UDP_IP, UDP_PORT_plotter2player))


    def update(self, data_dict):
        self.t += self.dt
        keep = self.points[:, -1] > self.t
        self.points_colors = self.points_colors[keep]
        self.points = self.points[keep, :]  # delete old points
        if data_dict is not None:
            # print(data_dict)
            if 'dur' in data_dict:
                point_dur = data_dict['dur']
            else:
                point_dur = self.default_point_dur
            if 'size_factor' in data_dict:
                size_factor = data_dict['size_factor']
            else:
                size_factor = self.default_size_factor
            point_size = data_dict['gain'] * size_factor
            new_point = [self.df.iloc[data_dict['idx']]['col_x'],
                         self.df.iloc[data_dict['idx']]['col_y'],
                         point_size,
                         self.t + point_dur
                         ]
            self.points = np.vstack([self.points, new_point])  # add new point
            if 'c' in data_dict:
                color = data_dict['c']
            else:
                color = self.default_color
            self.points_colors = np.append(self.points_colors, color)
            print(f'{len(self.points)}', data_dict)

        self.p.set_visible(True)
        if len(self.points) > 0:
            self.p.set_offsets(self.points[:, :2])
            self.p.set_color(self.points_colors)
            self.p.set_sizes(self.points[:, 2])
            self.points[:, 2] *= 0.9
        else:
            self.p.set_visible(False)
        for i, (k, v) in enumerate(self.clicked_key_vals.items()):
            self.texts[i].set_text(k)
            self.texts[i].set_position(v)
            self.texts[i].set_color('w')
            self.texts[i].set_visible(True) 
        for i in range(len(self.clicked_key_vals), len(self.texts)):
            self.texts[i].set_visible(False)
        return self.p, *self.texts
    
    def on_motion(self, event):
        if not self.poiter_clicked:
            return
        if len(self.clicked_key_vals) > self.num_text_elements:
            return
        # print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
        #     ('double' if event.dblclick else 'single', event.button,
        #     event.x, event.y, event.xdata, event.ydata))
        self.clicked_key_vals[self.selected_key] = event.xdata, event.ydata
        sock_plotter2player.sendto(json.dumps(self.clicked_key_vals).encode('utf-8'), (UDP_IP, UDP_PORT_plotter2player))
        # print('*'*40)
        # print(self.clicked_key_vals)
        # print('~'*40)
    
    def on_click(self, event):
        if event.button == 1:
            self.poiter_clicked = True
            self.clicked_key_vals[self.selected_key] = event.xdata, event.ydata
            sock_plotter2player.sendto(json.dumps(self.clicked_key_vals).encode('utf-8'), (UDP_IP, UDP_PORT_plotter2player))
        else:
            self.poiter_clicked = False
    
    def on_release(self, event):
        if event.button == 1:
            self.poiter_clicked = False

    def on_press(self, event):
        if event.key == 'tab':
            self.clicked_key_vals = {}
            for t in self.texts:
                t.set_visible(False)
            return
        if event.key == 'backspace':
            if self.selected_key in self.clicked_key_vals:
                del self.clicked_key_vals[self.selected_key]
            return
        print('press', event.key)
        self.selected_key = event.key
        sys.stdout.flush()



def get_updated_val(update_val=None):
    if not hasattr(get_updated_val, 'val'):
        get_updated_val.val = 0
    if update_val is not None:
        get_updated_val.val = update_val
    return get_updated_val.val


def emitter():
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            while len(scope.points) > MAX_POINTS_IN_QUEUE:
                # empty the queue if needed
                # (this points will not be plotted but at least the plot will keep sync)
                data, addr = sock.recvfrom(1024)
            data_dict = json.loads(data)

        except socket.error:
            data_dict = None

        yield data_dict


df = load_df()

interval = 1
dt_ = interval / 1000
sock.settimeout(0)
sock_plotter2player.settimeout(0)

fig_, ax_ = plt.subplots(figsize=(10, 10))

scope = Scope(fig_, ax_, df, dt_)
ani = animation.FuncAnimation(fig_, scope.update, emitter, interval=interval,
                              blit=True)
plt.show()
