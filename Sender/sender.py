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
sRTT = 15

def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    logging.info("Socket created")
    return sock

def start_processes(sock):
    manager = Manager()
    shared_dict = manager.dict()
    timeout = manager.Value(10)
    listener_process = Process(target=recieve, args=(shared_dict, sock, timeout))
    response_process = Process(target=send, args=(shared_dict, sock, timeout))
    listener_process.start()
    response_process.start()
    keyboard(listener_process, response_process)

def recieve(shared_dict, sock, timeout):
    while True:
        data, adress = sock.recvfrom(4096)
        unpacked_data = unpack_data(data)
        RTT = time.time() - shared_dict[unpacked_data[0]][0]
        sRTT = get_estimated_rtt(RTT)
        timeout = 2 * sRTT
        shared_dict[unpacked_data[0]] = (RTT, sRTT, timeout)
        logging.info("RECV: " + str(unpack_data(data)))
        logging.info("RECV: " + str(adress))

def send(shared_dict, sock, timeout):
    sieve.extend(200)
    try:
        for x in range(200):
            time.sleep(1)
            logging.info("DICT: " + str(shared_dict))
            shared_dict[x] = (time.time(), 0, TimeOut)
            if x in sieve:
                data = pack_data(x, True, False)
                resend_thread = Thread(target=resend, args=((x, True, True), sock, timeout))
                resend_thread.start()
            else:
                data = pack_data(x, False, False)
                
            logging.info("SEND: " + str(struct.unpack("=B??", data)))
            _ = sock.sendto(data, (IP, PORT))
    finally:
        logging.info("CLOSING")
        sock.close()

def resend(segment, sock, timeout):
    print(timeout)
    data = pack_data(segment[0], segment[1], segment[2])
    time.sleep(timeout)
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

def unpack_data(package_num):
    fmt = "=B"
    return struct.unpack(fmt, package_num)

def get_estimated_rtt(RTT):
    return ALPHA * sRTT + (1 - ALPHA) * RTT

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='(%(asctime)s %(levelname)s) %(message)s', 
        datefmt='%H:%M:%S')
    sock = create_socket()
    start_processes(sock)
