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
init_time = time.time()

def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return sock

def start_processes(sock):
    manager = Manager()
    shared_dict = manager.dict()  # (RTT, retransmit)
    wnd_dict = manager.dict() # cwnd, cwmax, effwnd
    wnd_dict['cwnd'] = CWINI
    wnd_dict['cwmax'] = CWMAX
    wnd_dict['effwnd'] = 10
    timeout = manager.Value('timeout', 10.0)
    last_ack = manager.Value('last_ack', -1)
    last_sent = manager.Value('last_sent', -1)
    sRTT = manager.Value("sRTT", 10)
    listener_process = Process(target=recieve, args=(shared_dict, sock, timeout, wnd_dict, last_ack, last_sent, sRTT))
    response_process = Process(target=send, args=(shared_dict, sock, timeout, wnd_dict, last_ack, last_sent, sRTT))
    listener_process.start()
    response_process.start()
    keyboard(listener_process, response_process)

def recieve(shared_dict, sock, timeout, wnd_dict, last_ack, last_sent, sRTT):
    while True:
        data, _ = sock.recvfrom(4096)
        pack_num = unpack_data(data)[0]
        if pack_num > last_ack.value:
            update_congestion_window(wnd_dict)
            last_ack.value = pack_num
            wnd_dict['effwnd'] = int(wnd_dict['cwnd'] - ((last_sent.value+1) - (last_ack.value+1)))
            if not shared_dict[last_ack.value][1]:
                RTT = time.time() - shared_dict[last_ack.value][0]
                get_estimated_rtt(RTT, sRTT)
                timeout.value = (2 * sRTT.value)
                shared_dict[last_ack.value] = (RTT, shared_dict[last_ack][1]) # (RTT, retransmit)
                print(str(last_ack.value) + '|' + str(round(time.time() - init_time, 2)) + '|RECIEVE|' + str(wnd_dict['effwnd']) + '|' +  str(wnd_dict['cwnd']) + '|' + str(round(RTT, 2)) + '|' + str(round(sRTT.value, 2)) + '|' + str(round(timeout.value, 2))) # (RTT, sRTT, timeout, retransmit, recived)
            else:
                rtt = time.time() - shared_dict[last_ack.value][0]
                shared_dict[last_ack.value] = (rtt, shared_dict[last_ack][1]) # (RTT, retransmit)
                print(str(last_ack.value) + '|' + str(round(time.time() - init_time, 2)) + '|RECIEVE|' + str(wnd_dict['effwnd']) + '|' +  str(wnd_dict['cwnd']) + '|' + str(round(rtt, 2)) + '|' + str(round(sRTT.value, 2)) + '|' + str(round(timeout.value, 2)))

def update_congestion_window(wnd_dict):
    if wnd_dict['cwnd'] < wnd_dict['cwmax']:
        wnd_dict['cwnd'] += 1
    else:
        wnd_dict['cwnd'] += round(1/wnd_dict['cwnd'])
        wnd_dict['cwmax'] = min(CWMAX, wnd_dict['cwnd'])

def send(shared_dict, sock, timeout, wnd_dict, last_ack, last_sent, sRTT):
    x = 0
    wait_time = time.time()
    try:
        while time.time() - init_time <= 200:
            if wnd_dict['effwnd'] > 0:
                shared_dict[x] = (time.time(), False) # (RTT, retransmit)
                last_sent.value = x
                if x in sieve:
                    resend_thread = Thread(target=resend, args=(x, sock, timeout, shared_dict, wnd_dict, last_ack, sRTT))
                    resend_thread.start()
                else:
                    data = pack_data(x)
                    _ = sock.sendto(data, (IP, PORT))
                    resend_thread = Thread(target=resend, args=(x, sock, timeout, shared_dict, wnd_dict, last_ack, sRTT))
                    resend_thread.start()
                wnd_dict['effwnd'] = int(wnd_dict['cwnd'] - ((last_sent.value+1) - (last_ack.value+1)))
                print(str(x) + '|' + str(round(time.time() - init_time, 2)) + '|SEND|' + str(wnd_dict['effwnd']) + '|' +  str(wnd_dict['cwnd']) + '|' + '0' + '|' + str(round(sRTT.value, 2)) + '|' + str(round(timeout.value, 2)))
                x+=1
                wait_time = time.time()
            while time.time() - wait_time <= 1:
                    pass
    except:
        print(sys.exc_info()[1])
    finally:
        while last_ack.value <= 200:
            pass
        sock.close()
        sys.exit()

def resend(segm_num, sock, timeout, shared_dict, wnd_dict, last_ack, sRTT):
    time_ini = time.time()
    data = pack_data(segm_num)
    tmout = timeout.value
    while(time.time() - time_ini <=tmout):
        pass
    if last_ack.value < segm_num:
        shared_dict[segm_num] = (shared_dict[segm_num][0], True)# (RTT, retransmit)
        timeout.value = 2 * timeout.value  # Karn/Partridge algorithm
        update_congestion_window_on_timeout(wnd_dict) # When TimeOut

        print(str(segm_num) + '|' + str(round(time.time() - init_time, 2)) + '|RESEND|' + str(wnd_dict['effwnd']) + '|' +  str(wnd_dict['cwnd']) + '|' + '0' + '|' + str(round(sRTT.value, 2)) + '|' + str(round(timeout.value, 2)))
        _ = sock.sendto(data, (IP, PORT))

def update_congestion_window_on_timeout(wnd_dict):
    wnd_dict['cwnd'] = CWINI
    wnd_dict['cwmax'] = max(CWINI, round(wnd_dict['cwmax']/2))

def keyboard(listener_process, response_process):
    while True:
        inpt = input()
        if inpt == 'f' or inpt == 'F':
            listener_process.terminate()
            response_process.terminate()
            sys.exit()

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
