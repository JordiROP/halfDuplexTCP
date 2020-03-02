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
sRTT = 5
cwini = 1

def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return sock

def start_processes(sock):
    manager = Manager()
    shared_dict = manager.dict()  # (RTT, sRTT, timeout, cwnd, eff_wnd)
    wnd_dict = manager.dict()
    wnd_dict['cwnd'] = 1
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
        oldest_pack = unpacked_data[0]
        while oldest_pack in ack_dict and not ack_dict[oldest_pack]: 
            ack_dict[unpacked_data[0]] = True
            oldest_pack -= 1
        oldest_pack +=1
        last_ack.value = unpacked_data[0]
        wnd_dict['effwnd'] = int(wnd_dict['cwnd'] - ((list(ack_dict.keys())[-1]+1) - (last_ack.value+1)))
        for pack_num in range(oldest_pack, last_ack.value+1):
            if not unpacked_data[1]:
                RTT = time.time() - shared_dict[pack_num][0]
                sRTT = get_estimated_rtt(RTT, shared_dict[pack_num][1])
                shared_dict[pack_num] = (RTT, sRTT, timeout.value, wnd_dict['cwnd'], wnd_dict['effwnd'])
                timeout.value = (2 * sRTT)
        print(str(round(time.time())) + '|RECIEVE|' + str(wnd_dict['effwnd']) + '|' +  str(wnd_dict['cwnd']) + '|' + str(round(shared_dict[last_ack.value][0], 2)) + '|' + str(round(shared_dict[last_ack.value][1], 2)) + '|' + str(round(shared_dict[last_ack.value][2], 2)))

def send(shared_dict, sock, timeout, wnd_dict, ack_dict, last_ack):
    sieve.extend(200)
    x = 0
    init_time = time.time()
    try:
        while time.time() - init_time <= 200:
            if wnd_dict['effwnd'] > 0:
                time.sleep(1)
                ini_sRTT = sRTT if (x == 0 or (x-1) in sieve) else shared_dict[last_ack.value][1]
                # if we loose a package we want to start over again instead of taking the last good package
                shared_dict[x] = (time.time(), ini_sRTT, timeout.value, 0, 0) 
                if x in sieve:
                    data = pack_data(x, True, False)
                    resend_thread = Thread(target=resend, args=((x, True, True), sock, timeout, shared_dict, wnd_dict, last_ack))
                    resend_thread.start()
                else:
                    data = pack_data(x, False, False)
                    ack_dict[x] = False
                    _ = sock.sendto(data, (IP, PORT))
                wnd_dict['effwnd'] = int(wnd_dict['cwnd'] - ((x+1) - (last_ack.value+1)))
                print(str(round(time.time())) + '|SEND|' + str(wnd_dict['effwnd']) + '|' +  str(wnd_dict['cwnd']) + '|' + str(round(shared_dict[x][0], 2)) + '|' + str(round(shared_dict[x][1], 2)) + '|' + str(round(shared_dict[x][2], 2)))
                x+=1
    except:
        print(sys.exc_info()[0])
    finally:
        while last_ack.value <= 200:
            pass
        sock.close()
        sys.exit()

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
    print(str(round(time.time())) + '|RESEND|' + str(wnd_dict['effwnd']) + '|' +  str(wnd_dict['cwnd']) + '|' + str(round(shared_dict[segment[0]][0], 2)) + '|' + str(round(shared_dict[segment[0]][1], 2)) + '|' + str(round(shared_dict[segment[0]][2], 2)))
    _ = sock.sendto(data, (IP, PORT))

def keyboard(listener_process, response_process):
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
    print("Time|Event|Eff.Win|cwnd|RTT|sRTT|TOut")
    sock = create_socket()
    start_processes(sock)
