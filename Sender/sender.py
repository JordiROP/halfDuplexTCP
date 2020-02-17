from threading import Thread
from multiprocessing import Process, Manager
from sympy import sieve

import logging
import socket
import sys
import time

IP = '127.0.0.1'
PORT = 20001

def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    logging.info("Socket created")
    return sock

def start_processes(sock):
    manager = Manager()
    shared_queue = manager.Queue()
    listener_process = Process(target=recieve, args=(shared_queue, sock))
    response_process = Process(target=send, args=(shared_queue, sock))
    listener_process.start()
    response_process.start()
    keyboard(listener_process, response_process)

def recieve(shared_queue, sock):
    while True:
        data, adress = sock.recvfrom(4096)
        print("RECV: " + str(data))
        print("RECV: " + str(adress))

def send(shared_queue, sock):
    message = {'num': None, 'ignore': False}
    sieve.extend(200)
    try:
        for x in range(200):
            time.sleep(1)
            if x in sieve:
                message['ignore'] = True
            print("SEND: " + str(message))
            sent = sock.sendto(str.encode(str(message)), (IP, PORT))
            print("SENT: " + str(sent))
    finally:
        print("CLOSING")
        sock.close()

def keyboard(listener_process, response_process):
    logging.info('Keyboard listening')
    while True:
        inpt = input()
        if inpt == 'f' or inpt == 'F':
            listener_process.terminate()
            response_process.terminate()
            sys.exit()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sock = create_socket()
    start_processes(sock)
