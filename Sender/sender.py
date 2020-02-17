import socket
import sys
import time

IP = '127.0.0.1'
PORT = 20001

def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    message = str.encode('Hi, im the client')
    try:
        for x in range(5):
            time.sleep(2)
            # Send data
            print("SEND: " + str(message))
            sent = sock.sendto(message, (IP, PORT))
            print("SENT: " + str(sent))

        # Receive response
        print("Waiting response")
        data, adress = sock.recvfrom(4096)
        print("RECV: " + str(data))
        print("RECV: " + str(adress))
    finally:
        print("CLOSING")
        sock.close()

if __name__ == "__main__":
    create_socket()