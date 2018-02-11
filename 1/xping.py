#!/usr/bin/env python

import os, sys, socket, struct, select, time, threading, hashlib

default_timer = time.time

ICMP_ECHO_REQUEST = 8

LOCK = threading.Lock()


def log(text):
    with LOCK:
        print('[' + threading.current_thread().getName() + '] ' + text)


def checksum(text):
    sum = 0
    countTo = (len(text) / 2) * 2
    count = 0
    while count < countTo:
        thisVal = ord(text[count + 1]) * 256 + ord(text[count])
        sum += thisVal
        count += 2

    if countTo < len(text):
        sum += ord(text[len(text) - 1])

    sum = (sum >> 16) + (sum & 0xffff)
    sum += sum >> 16
    answer = ~sum
    answer &= 0xffff

    answer = answer >> 8 | (answer << 8 & 0xff00)

    return answer


class ParallelPinger(threading.Thread):
    def __init__(self, host):
        super(ParallelPinger, self).__init__()
        self.host = host

    def run(self):
        super(ParallelPinger, self).run()
        self.do_ping()

    @staticmethod
    def _receive_one_ping(socket_obj, expected_port, timeout):
        time_left = timeout
        while True:
            start_time = time.time()
            ready = select.select([socket_obj], [], [], time_left)
            select_time = time.time() - start_time
            if not ready[0]:
                return

            end_time = time.time()
            payload, addr = socket_obj.recvfrom(1024)
            header = payload[20:28]
            type, code, checksum, actual_port, sequence = struct.unpack(
                "bbHHh", header
            )

            if type != 8 and expected_port == actual_port:
                double_size = struct.calcsize("d")
                time_field = struct.unpack("d", payload[28:28 + double_size])[0]
                return end_time - time_field

            time_left = time_left - select_time
            if time_left <= 0:
                return

    def _send_one_ping(self, my_socket, port):
        my_checksum = 0

        header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, my_checksum, port, 1)
        double_size = struct.calcsize("d")
        data = (192 - double_size) * "Q"
        data = struct.pack("d", time.time()) + data

        my_checksum = checksum(header + data)

        header = struct.pack(
            "bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), port, 1
        )
        packet = header + data
        my_socket.sendto(packet, (self.host, 1))

    def do_one(self, timeout):
        icmp = socket.getprotobyname("icmp")
        try:
            my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
        except socket.error, (errno, msg):
            if errno == 1:
                msg += " - Note that ICMP messages can only be sent from processes"
                raise socket.error(msg)
            raise

        thread_id = checksum(threading.current_thread().getName()) & 0xFFFF

        self._send_one_ping(my_socket, thread_id)
        delay = self._receive_one_ping(my_socket, thread_id, timeout)

        my_socket.close()
        return delay

    def do_ping(self, timeout=1, count=4):
        log("PING {}".format(self.host))
        for i in xrange(count):

            try:
                delay = self.do_one(timeout)
            except socket.gaierror, e:
                log("FAILED. Socket Error: '%s')".format(e[1]))
                break

            if delay is None:
                log("Request timeout for {}".format(self.host))
            else:
                delay *= 1000
                log("X bytes from {}: time = {:.2f} ms".format(self.host, delay))
        print


if __name__ == '__main__':

    assert len(sys.argv) > 1

    threads = []
    for host in sys.argv[1:]:
        thread = ParallelPinger(host)
        threads.append(thread)
        thread.setDaemon(True)
        thread.start()

    [thread.join() for thread in threads]

