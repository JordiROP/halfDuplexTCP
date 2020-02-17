from threading import Thread
import socket
import sys
import logging
IP = '127.0.0.1'
PORT = 20001

buffer_queue = []
def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP, PORT))
    logging.info("Socket created")
    return sock

def start_threads(sock):
    listener_thread = Thread(target=listen, args=(sock,))
    response_thread = Thread(target=response, args=(sock,))
    listener_thread.start()
    response_thread.start()
    return listener_thread, response_thread

def listen(sock):
    global buffer_queue
    logging.info("Server listening")
    try:
        while True: 
            # Receive data
            data, address = sock.recvfrom(4096)
            logging.info("RECV: " + str(data))
            logging.info("RECV: " + str(address))
            buffer_queue.append((data, address))

    finally:
        logging.info("CLOSING")
        sock.close()

def response(sock):
    global buffer_queue
    try:
        while True:
            if len(buffer_queue) != 0:
                segment = buffer_queue.pop()
                address = segment[1]
                message = str.encode("Server response")
                # Send data
                logging.info("SEND: " + str(message))
                logging.info("SEND: " + str(address))
                sent = sock.sendto(message, address)
                logging.info("SENT: " + str(sent))
    finally:
        logging.info("CLOSING")
        sock.close()

def keyboard(listener_thread, response_thread):
    while True:
        inpt = input()
        if inpt == 'f' or inpt == 'F':
            listener_thread.join()
            response_thread.join()
            sys.exit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sock = create_socket()
    listener_thread, response_thread = start_threads(sock)
    keyboard(listener_thread, response_thread)