from threading import Thread
from multiprocessing import Process, Manager
from sympy import sieve

import struct
import logging
import socket
import sys
import time

IP = '127.0.0.1'
PORT = 20001
ALPHA = 0.8
CWMAX = 4
sRTT = 5
cwini = 1 # MSS

adv_wnd = sys.maxsize

def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    logging.info("Socket created")
    return sock

def start_processes(sock):
    manager = Manager()
    shared_dict = manager.dict()  # (RTT, sRTT, timeout, cwnd, eff_wnd)
    wnd_dict = manager.dict()
    wnd_dict['cwnd'] = 1.0
    wnd_dict['cwmax'] = CWMAX
    wnd_dict['effwnd'] = 10
    ack_dict = manager.dict()
    timeout = manager.Value('timeout', 10.0)
    last_ack = manager.Value('last_ack', -1)
    listener_process = Process(target=recieve, args=(shared_dict, sock, timeout, wnd_dict, ack_dict, last_ack))
    response_process = Process(target=send, args=(shared_dict, sock, timeout, wnd_dict, ack_dict, last_ack))
    listener_process.start()
    response_process.start()
    keyboard(listener_process, response_process)

def recieve(shared_dict, sock, timeout, wnd_dict, ack_dict, last_ack):
    while True:
        data, _ = sock.recvfrom(4096)
        unpacked_data = unpack_data(data)
        RTT = 0
        if wnd_dict['cwnd'] < wnd_dict['cwmax']:
            wnd_dict['cwnd'] += 1
        else:
            wnd_dict['cwnd'] += int(1/wnd_dict['cwnd'])
            wnd_dict['cwmax'] = min(CWMAX, wnd_dict['cwnd'])
        wnd_dict['effwnd'] = int(wnd_dict['cwnd'] - ((list(ack_dict.keys())[-1]+1) - (last_ack.value+1)))
        oldest_pack = unpacked_data[0]
        while oldest_pack in ack_dict and not ack_dict[oldest_pack]: 
            ack_dict[unpacked_data[0]] = True
            oldest_pack -= 1
        oldest_pack +=1
        last_ack.value = unpacked_data[0]

        for pack_num in range(oldest_pack, last_ack.value+1):
            if not unpacked_data[1]:
                RTT = time.time() - shared_dict[pack_num][0]
                sRTT = get_estimated_rtt(RTT, shared_dict[pack_num][1])
                shared_dict[pack_num] = (RTT, sRTT, timeout.value, wnd_dict['cwnd'], wnd_dict['effwnd'])
                timeout.value = (2 * sRTT)
        logging.info("RECV: " + str(unpacked_data[0]))

def send(shared_dict, sock, timeout, wnd_dict, ack_dict, last_ack):
    sieve.extend(200)
    x = 0
    try:
        while x <= 200:
            if wnd_dict['effwnd'] > 0:
                time.sleep(1)
                logging.info("DICT: " + str(shared_dict))
                ini_rss = sRTT if (x == 0 or (x-1) in sieve) else shared_dict[last_ack.value][1]
                
                # if we loose a package we want to start over again instead of taking the last good package
                shared_dict[x] = (time.time(), ini_rss, timeout.value, 0, 0) 
                if x in sieve:
                    data = pack_data(x, True, False)
                    resend_thread = Thread(target=resend, args=((x, True, True), sock, timeout, shared_dict, wnd_dict, last_ack))
                    resend_thread.start()
                else:
                    data = pack_data(x, False, False)
                    ack_dict[x] = False
                    logging.info("SEND: " + str(struct.unpack("=B??", data)))
                    _ = sock.sendto(data, (IP, PORT))
                wnd_dict['effwnd'] = int(wnd_dict['cwnd'] - ((x+1) - (last_ack.value+1)))
                logging.info(" -- CONGESTION WINDOW: " + str(wnd_dict['cwnd']))
                logging.info(" -- LAST SEND: " + str(x))
                logging.info(" -- LAST ACK: " + str(last_ack.value))
                logging.info("EFFECTIVE_WINDOW SEND: " + str(wnd_dict['effwnd']))
                x+=1
    finally:
        while last_ack.value <= 200:
            pass
        logging.info("CLOSING")
        sock.close()

def resend(segment, sock, timeout, shared_dict, wnd_dict, last_ack):
    time_ini = time.time()
    while(time.time() - time_ini <=timeout.value):
        pass
    timeout.value = 2 * timeout.value  # Karn/Partridge algorithm

    data = pack_data(segment[0], segment[1], segment[2])

    # When TimeOut
    wnd_dict['cwnd'] = cwini
    wnd_dict['cwmax'] = max(cwini, int(wnd_dict['cwmax']/2))

    shared_dict[segment[0]] = (shared_dict[segment[0]][0], sRTT, timeout.value, wnd_dict['cwnd'], int(shared_dict[segment[0]][4]))  # Measuring RTT only when no retransmission
    logging.info("RESEND: " + str(struct.unpack("=B??", data)))
    _ = sock.sendto(data, (IP, PORT))

def keyboard(listener_process, response_process):
    logging.info('Keyboard listening')
    while True:
        inpt = input()
        if inpt == 'f' or inpt == 'F':
            listener_process.terminate()
            response_process.terminate()
            sys.exit()

def pack_data(package_num, prime, resend):
    fmt = "=B??"
    return struct.pack(fmt, package_num, prime, resend)

def unpack_data(data):
    fmt = "=B?"
    return struct.unpack(fmt, data)

def get_estimated_rtt(RTT, sRTT):
    return ALPHA * sRTT + (1 - ALPHA) * RTT

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='(%(asctime)s %(levelname)s) %(message)s', 
        datefmt='%H:%M:%S')
    sock = create_socket()
    start_processes(sock)
