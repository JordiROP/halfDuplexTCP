from threading import Thread
from multiprocessing import Process, Manager
from sympy import sieve

import time
import struct
import socket
import sys
import logging

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
    shared_queue = manager.dict()
    last_package_ack = manager.Value('last_package_ack', -1)
    buffer_size = manager.Value('buffer_size', 0)
    listener_process = Process(target=listen, args=(shared_queue, sock, last_package_ack, buffer_size))
    response_process = Process(target=response, args=(shared_queue, sock, last_package_ack, buffer_size))
    listener_process.start()
    response_process.start()
    keyboard(listener_process, response_process)

def listen(shared_queue, sock, last_package, buffer_size):
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
                shared_queue[package_num] = ((data, address), time.time())
                cwnd[package_num] = len(shared_queue)
                buffer_size.value += 1
                logging.info("BUFFERSIZE: " + str(buffer_size.value))

    finally:
        logging.info("CLOSING")
        sock.close()

def response(shared_queue, sock, last_package_ack, buffer_size):
    sieve.extend(200)
    try:
        while True:
            segment = None
            if 0 < buffer_size.value < 3:
                packg_num = last_package_ack.value + 1
                if (packg_num in shared_queue) and (time.time() - shared_queue[packg_num][1] >= 2.0):
                    segment = (packg_num, shared_queue[packg_num][0], shared_queue[packg_num][1])
                    del shared_queue[packg_num]
                    buffer_size.value -= 1
                    last_package_ack.value = packg_num
            elif buffer_size.value > 2:
                segment = get_last_segment(buffer_size, shared_queue, last_package_ack)
            if segment:
                response_thread = Thread(target=send_response, args=(segment,))
                response_thread.start()
                logging.info("BUFFER SIZE: " + str(buffer_size.value))
                logging.info("LAST ACK: " + str(last_package_ack.value))
    finally:
        logging.info("CLOSING")
        sock.close()

def get_last_segment(buff_size, shared_queue, last_package_ack):
    segment = None
    packg_num = last_package_ack.value + 1
    while packg_num in shared_queue:
        segment = (packg_num, shared_queue[packg_num][0], shared_queue[packg_num][1])
        del shared_queue[packg_num]
        last_package_ack.value = packg_num
        packg_num += 1
        buff_size.value -= 1
    return segment

    
def send_response(segment):
    package_num = pack_data(segment[0])
    address = segment[1][1]
    logging.info("SEND Package# ACK: " + str(struct.unpack('=B?',package_num)[0]))
    _ = sock.sendto(package_num, address)
    exit()

def keyboard(listener_process, response_process):
    while True:
        inpt = input()
        if inpt == 'f' or inpt == 'F':
            listener_process.terminate()
            response_process.terminate()
            sys.exit()

def pack_data(package_num):
    fmt = "=B?"
    is_prime = False
    if package_num in sieve:
        is_prime = True
    return struct.pack(fmt, package_num, is_prime)

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
