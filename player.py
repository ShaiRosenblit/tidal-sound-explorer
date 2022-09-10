from pythonosc import udp_client
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher
import asyncio
import pandas as pd
from scipy.spatial import KDTree
import socket
import json
import numpy as np

from utils import load_df

ip = "127.0.0.1"
udt_port = 5005
server_port = 57121
client_port = 57120


def send_message_to_tidal(message_dict):
    if 'filter_sample' in message_dict:
        is_filt = (df.s == message_dict['filter_sample'])
        filt_idx = df.loc[is_filt].index
        filt_xy = df.loc[is_filt, ['col_x', 'col_y']].values
        dists = ((filt_xy[:, 0] - message_dict['x'])**2 + (filt_xy[:, 1] - message_dict['y'])**2)**0.5
        sub_df_idx = np.argmin(dists)
        idx = filt_idx[sub_df_idx]
    else:
        _, idx = kdt.query([message_dict['x'], message_dict['y']])
    print(f'Playing smaple {df.iloc[idx]["seg_sound"]}, '
          f'{df.iloc[idx]["seg_number_in_sample"]}, '
          f'cycle - {message_dict["cycle"]}')
    # message_dict.pop('x')
    # message_dict.pop('y')
    # message_dict.pop('c')
    message_list = [
        "s", df.iloc[idx]['s'],
        "n", int(df.iloc[idx]['n']),
        "begin", df.iloc[idx]['seg_start'],
        "end", df.iloc[idx]['seg_end'],
        "sustain", 10,
    ]
    for k, v in message_dict.items():
        message_list.extend([k, v])

    client.send_message("/dirt/play", message_list)
    return idx


def update_func(*args):
    if not hasattr(update_func, 'x'):
        update_func.x = 0
        update_func.y = 0
    message_dict = dict(zip(args[1::2], args[2::2]))
    update_func.x = message_dict['x']
    update_func.y = message_dict['y']
    idx = send_message_to_tidal(message_dict)
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


if __name__ == "__main__":
    df = load_df()
    kdt = KDTree(df[['col_x', 'col_y']])
    client = udp_client.SimpleUDPClient("127.0.0.1", client_port)
    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP

    asyncio.run(main())
