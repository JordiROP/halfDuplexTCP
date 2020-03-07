from threading import Thread
from multiprocessing import Process, Manager
from sympy import sieve

import struct
import socket
import sys
import time

IP = '127.0.0.1'
PORT = 20001
ALPHA = 0.8
CWMAX = 4
CWINI = 1
EFFINI = 10
init_time = time.time()

def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return sock

def create_structures():
    manager = Manager()
    pkg_dict = manager.dict()  # (send time, retransmit)
    wnd_dict = manager.dict() # cwnd, cwmax, effwnd
    wnd_dict['cwnd'] = CWINI
    wnd_dict['cwmax'] = CWMAX
    wnd_dict['effwnd'] = EFFINI
    timeout = manager.Value('timeout', 10.0)
    last_ack = manager.Value('last_ack', -1)
    last_sent = manager.Value('last_sent', -1)
    sRTT = manager.Value("sRTT", 10)
    return pkg_dict, wnd_dict, timeout, last_ack, last_sent, sRTT

def start_processes(sock):
    pkg_dict, wnd_dict, timeout, last_ack, last_sent, sRTT = create_structures()
    listener_process = Process(target=recieve, args=(pkg_dict, sock, timeout, wnd_dict, last_ack, last_sent, sRTT))
    response_process = Process(target=send, args=(pkg_dict, sock, timeout, wnd_dict, last_ack, last_sent, sRTT))
    listener_process.start()
    response_process.start()
    keyboard(listener_process, response_process)

def recieve(pkg_dict, sock, timeout, wnd_dict, last_ack, last_sent, sRTT):
    while True:
        data, _ = sock.recvfrom(4096)
        pkg_num = unpack_data(data)[0]
        
        if last_ack < pkg_num: # If we have not already processed the package
            update_congestion_window(wnd_dict)
            last_ack.value = pkg_num
            update_effective_window(wnd_dict, (last_sent+1), (last_ack+1))
            RTT = time.time() - pkg_dict[pkg_num][0]
            if not pkg_dict[pkg_num][1]: #If the package has not been retransmited we calculate sRTT and timeout
                get_estimated_rtt(RTT, sRTT)
                timeout.value = (sRTT.value * 2)
            print(str(last_ack.value) + '|' + str(round(time.time() - init_time, 2)) + '|RECIEVE|' + str(wnd_dict['effwnd']) + '|' +  str(wnd_dict['cwnd']) + '|' + str(round(RTT, 2)) + '|' + str(round(sRTT.value, 2)) + '|' + str(round(timeout.value, 2))) # (RTT, sRTT, timeout, retransmit, recived)

                

def send(pkg_dict, sock, timeout, wnd_dict, last_ack, last_sent, sRTT):
    pass

def resend(segm_num, sock, timeout, pkg_dict, wnd_dict, last_ack, sRTT):
    time.sleep(timeout.value)

    if segm_num > last_ack: # If we have received the the segment num while waiting for the timeout the package has been received on time
        pkg_dict[segm_num] = (pkg_dict[segm_num][0], True)# (send time, retransmit)
        timeout.value = 2 * timeout.value  # Karn/Partridge algorithm if a package is lost we double the timeout
        update_congestion_window_on_timeout(wnd_dict) # When TimeOut
        data = pack_data(segm_num)
        _ = sock.sendto(data, (IP, PORT))
        print(str(segm_num) + '|' + str(round(time.time() - init_time, 2)) + '|RESEND|' + str(wnd_dict['effwnd']) + '|' +  str(wnd_dict['cwnd']) + '|' + '0' + '|' + str(round(sRTT.value, 2)) + '|' + str(round(timeout.value, 2)))

def keyboard(listener_process, response_process):
    while True:
        inpt = input()
        if inpt == 'f' or inpt == 'F':
            listener_process.terminate()
            response_process.terminate()
            sys.exit()

def update_effective_window(wnd_dict, num_pkg_sent, num_pkg_ack):
    wnd_dict['effwnd'] = round(wnd_dict['cwnd'] - (num_pkg_sent - num_pkg_ack))

def update_congestion_window(wnd_dict):
    if wnd_dict['cwnd'] < wnd_dict['cwmax']:
        wnd_dict['cwnd'] += 1
    else:
        wnd_dict['cwnd'] += round(1/wnd_dict['cwnd'])
        wnd_dict['cwmax'] = min(CWMAX, wnd_dict['cwnd'])

def update_congestion_window_on_timeout(wnd_dict):
    wnd_dict['cwnd'] = CWINI
    wnd_dict['cwmax'] = max(CWINI, round(wnd_dict['cwmax']/2))

def pack_data(package_num):
    fmt = "=B"
    return struct.pack(fmt, package_num)

def unpack_data(data):
    fmt = "=B?"
    return struct.unpack(fmt, data)

def get_estimated_rtt(RTT, sRTT):
    sRTT.value = ALPHA * sRTT.value + (1-ALPHA) * RTT

if __name__ == "__main__":
    print("Pack.Num|Time|Event|Eff.Win|cwnd|RTT|sRTT|TOut")
    sock = create_socket()
    start_processes(sock)