from pythonosc import udp_client
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher
import asyncio
import pandas as pd
from scipy.spatial import KDTree
import socket
import json
import numpy as np
import functools

from utils import load_df

ip = "127.0.0.1"
udt_port = 5005
server_port = 57121
client_port = 57120


def send_message_to_tidal(message_dict):
    filters = tuple((k, v) for k, v in message_dict.items() if k.startswith('keep_only'))
    filt_idx = filter_df(filters)
    if len(filt_idx) == 0:
        return
    query_cols = []
    query_vals = []
    for k, v in message_dict.items():
        if k.startswith('query_'):
            query_cols.append(k[6:])
            query_vals.append(v)

    filt_sub_space = df.loc[filt_idx, query_cols].values
    if len(query_cols) > 0:
        if 'nth_nearest' in message_dict:
            nth_nearest = int(message_dict['nth_nearest'])
        else:
            nth_nearest = 0
        dists = ((filt_sub_space - query_vals)**2).sum(axis=1)
        nth_nearest = min(nth_nearest, (len(dists) - 1))
        sub_df_idx = np.argpartition(dists, nth_nearest)[nth_nearest]
        idx = filt_idx[sub_df_idx]
    else:
        idx = np.random.choice(filt_idx)

    print(f'Playing smaple {df.iloc[idx]["seg_sound"]}, '
          f'{df.iloc[idx]["seg_number_in_sample"]}, '
          f'cycle - {message_dict["cycle"]}')
    message_list = [
        "s", df.iloc[idx]['s'],
        "n", int(df.iloc[idx]['n']),
        "begin", df.iloc[idx]['seg_start'],
        "end", df.iloc[idx]['seg_end'],
        "sustain", 10,
    ]
    for k, v in message_dict.items():
        if v is None:
            v = 0
        message_list.extend([k, v])
    client.send_message("/dirt/play", message_list)
    return idx


def update_func(*args):
    if not hasattr(update_func, 'x'):
        update_func.x = 0
        update_func.y = 0
    message_dict = dict(zip(args[1::2], args[2::2]))
    if "s" in message_dict:
        return 
    if ('x' not in message_dict) or ('y' not in message_dict):
        message_dict['x'] = None
        message_dict['y'] = None

    update_func.x = message_dict['x']
    update_func.y = message_dict['y']
    idx = send_message_to_tidal(message_dict)
    if idx is not None:
        message_dict['idx'] = int(idx)
        if 'gain' not in message_dict:
            message_dict['gain'] = 1
        # print(message_dict)
        sock.sendto(json.dumps(message_dict, indent=2).encode('utf-8'), (ip, udt_port))


dispatcher = Dispatcher()
dispatcher.set_default_handler(update_func)


async def loop():
    print('Here we go!!!')
    while True:
        await asyncio.sleep(0)


async def main():

    server = AsyncIOOSCUDPServer((ip, server_port), dispatcher, asyncio.get_event_loop())
    transport, protocol = await server.create_serve_endpoint()  # Create datagram endpoint and start serving
    # await print_loop()
    # await loop()  # Enter main loop of program
    await asyncio.gather(loop())

    transport.close()  # Clean up serve endpoint


@functools.lru_cache(maxsize=None)
def filter_df(filters):
    print(f'filters - {filters}')
    if len(filters) == 0:
        return df.index

    filt_df = df
    for filt, val in filters:
        if filt.startswith('keep_only_above_'):
            filt_df = filt_df[filt_df[filt[16:]] > val]
        elif filt.startswith('keep_only_below_'):
            filt_df = filt_df[filt_df[filt[16:]] < val]
        elif filt.startswith('keep_only_equal_'):
            filt_df = filt_df[filt_df[filt[16:]] == val]
        elif filt.startswith('keep_only_start_'):
            filt_df = filt_df[filt_df[filt[16:]].str.startswith(val)]
        else:
            raise
    return filt_df.index


if __name__ == "__main__":
    global df
    df = load_df()
    kdt = KDTree(df[['col_x', 'col_y']])
    client = udp_client.SimpleUDPClient("127.0.0.1", client_port)
    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP

    asyncio.run(main())
