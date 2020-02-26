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
sRTT = 5

cwini = 1 # MSS
cwnd = 1  # MSS

adv_wnd = sys.maxsize

def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    logging.info("Socket created")
    return sock

def start_processes(sock):
    manager = Manager()
    shared_dict = manager.dict()  # (RTT, sRTT, timeout, cwnd, eff_wnd)
    ack_dict = manager.dict()
    timeout = manager.Value('timeout', 10.0)
    cwnd = manager.Value('cwnd', 1)
    cwmax = manager.Value('cwmax', 10)
    listener_process = Process(target=recieve, args=(shared_dict, sock, timeout, cwnd, cwmax, ack_dict))
    response_process = Process(target=send, args=(shared_dict, sock, timeout, cwnd, cwmax, ack_dict))
    listener_process.start()
    response_process.start()
    keyboard(listener_process, response_process)

def recieve(shared_dict, sock, timeout, cwnd, cwmax, ack_dict):
    while True:
        data, _ = sock.recvfrom(4096)
        unpacked_data = unpack_data(data)
        RTT = 0

        if cwnd.value < cwmax.value:
            cwnd.value = cwmax.value
        else:
            cwnd.value += 1/cwnd.value
            cwmax.value = min(cwmax.value, cwnd.value)

        oldest_pack = unpacked_data[0]
        while oldest_pack in ack_dict and not ack_dict[oldest_pack]: 
            ack_dict[unpacked_data[0]] = True
            oldest_pack -= 1
        oldest_pack +=1
        last_ack = unpacked_data[0]
        last_ack = [ack for ack in list(ack_dict.keys()) if ack_dict[ack] == True][-1]
        eff_wnd = cwnd.value - (list(ack_dict.keys())[-1] - last_ack) 
        # BiggestDictKey - BiggestDictKey with True

        for pack_num in range(oldest_pack, last_ack+1):
            print("PACK_NUM: " + str(pack_num))
            RTT = time.time() - shared_dict[pack_num][0]
            sRTT = get_estimated_rtt(RTT)
            shared_dict[pack_num] = (RTT, sRTT, timeout.value, int(cwnd.value), int(eff_wnd))
            if not unpacked_data[1]:
                timeout.value = (2 * sRTT)
            logging.info("RECV: " + str(unpack_data(data)))

def send(shared_dict, sock, timeout, cwnd, cwmax, ack_dict):
    sieve.extend(200)
    try:
        for x in range(200):
            time.sleep(1)
            logging.info("DICT: " + str(shared_dict))
            shared_dict[x] = (time.time(), 0, timeout.value, 0, 0)
            if x in sieve:
                data = pack_data(x, True, False)
                resend_thread = Thread(target=resend, args=((x, True, True), sock, timeout, shared_dict, cwnd, cwmax))
                resend_thread.start()
            else:
                data = pack_data(x, False, False)
            ack_dict[x] = False
            logging.info("SEND: " + str(struct.unpack("=B??", data)))
            _ = sock.sendto(data, (IP, PORT))
    finally:
        logging.info("CLOSING")
        sock.close()

def resend(segment, sock, timeout, shared_dict, cwnd, cwmax):
    time_ini = time.time()
    while(time.time() - time_ini <=timeout.value):
        pass
    timeout.value = 2 * timeout.value  # Karn/Partridge algorithm

    data = pack_data(segment[0], segment[1], segment[2])

    # When TimeOut
    cwnd.value = cwini
    cwmax.value = max(cwini, cwmax.value/2)

    shared_dict[segment[0]] = (shared_dict[segment[0]][0],shared_dict[segment[0]][1], timeout.value, int(cwnd.value), int(shared_dict[segment[0]][4]))  # Measuring RTT only when no retransmission
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

def get_estimated_rtt(RTT):
    return ALPHA * sRTT + (1 - ALPHA) * RTT

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='(%(asctime)s %(levelname)s) %(message)s', 
        datefmt='%H:%M:%S')
    sock = create_socket()
    start_processes(sock)
