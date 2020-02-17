from threading import Thread
from multiprocessing import Process, Manager

import struct
import socket
import sys
import logging
IP = '127.0.0.1'
PORT = 20001

def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP, PORT))
    logging.info("Socket created")
    return sock

def start_processes(sock):
    manager = Manager()
    shared_queue = manager.Queue()
    listener_process = Process(target=listen, args=(shared_queue, sock))
    response_process = Process(target=response, args=(shared_queue, sock))
    listener_process.start()
    response_process.start()
    keyboard(listener_process, response_process)

def listen(shared_queue, sock):
    logging.info("Server listening")
    try:
        while True: 
            # Receive data
            data, address = sock.recvfrom(4096)
            logging.info("RECV: " + str(struct.unpack('=B??' ,data)))
            logging.info("RECV: " + str(address))
            package_num = unpack_data(data)[0]
            shared_queue.put((package_num, (data, address)))

    finally:
        logging.info("CLOSING")
        sock.close()

def response(shared_queue, sock):
    try:
        while True:
            if not shared_queue.empty():
                segment = shared_queue.get()
                address = segment[1]
                message = pack_data(segment[0])
                # Send data
                logging.info("SEND: " + str(message))
                logging.info("SEND: " + str(address))
                sent = sock.sendto(message, address)
                logging.info("SENT: " + str(sent))
    finally:
        logging.info("CLOSING")
        sock.close()

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
    logging.basicConfig(level=logging.INFO)
    sock = create_socket()
    start_processes(sock)
