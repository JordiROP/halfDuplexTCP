from threading import Thread
from multiprocessing import Process, Manager

import typing
import time
import struct
import socket
import sys
import logging
import copy

IP = '127.0.0.1'
PORT = 20001
cwnd = {}

def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP, PORT))
    logging.info("Socket created")
    return sock

def start_processes(sock):
    manager = Manager()
    shared_queue = manager.list()
    listener_process = Process(target=listen, args=(shared_queue, sock))
    response_process = Process(target=response, args=(shared_queue, sock))
    listener_process.start()
    response_process.start()
    keyboard(listener_process, response_process)

def listen(shared_queue, sock):
    logging.info("Server listening")
    try:
        while True:
            data, address = sock.recvfrom(4096)
            unpacked_data = unpack_data(data) 
            package_num = unpacked_data[0]
            prime = unpacked_data[1]
            resent = unpacked_data[2]
            if not prime or resent:
                logging.info("RECV: " + str(struct.unpack('=B??', data)))
                shared_queue.append((package_num, (data, address)))
                cwnd[package_num] = len(shared_queue)
                logging.info("BUFFERSIZE: " + str(len(shared_queue)))

    finally:
        logging.info("CLOSING")
        sock.close()

def response(shared_queue, sock):
    try:
        while True:
            if len(shared_queue) != 0 :
                if len(shared_queue) < 3:
                    time.sleep(2.0)
                    segment = shared_queue.pop(0)
                    response_thread = Thread(target=send_response, args=(segment,))
                    response_thread.start()
                else:
                    queue_len = len(shared_queue)
                    for x in reversed(range(queue_len)):
                        segment = shared_queue.pop(x)
                        response_thread = Thread(target=send_response, args=(segment,))
                        response_thread.start()
                    
    finally:
        logging.info("CLOSING")
        sock.close()

def send_response(segment):
    package_num = pack_data(segment[0])
    address = segment[1][1]
    logging.info("SEND Package# ACK: " + str(struct.unpack('=B',package_num)[0]))
    _ = sock.sendto(package_num, address)
    exit()

def keyboard(listener_process, response_process):
    logging.info
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
    fmt = "=B??"
    return struct.unpack(fmt, data)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='(%(asctime)s %(levelname)s) %(message)s', 
        datefmt='%H:%M:%S')
    sock = create_socket()
    start_processes(sock)
