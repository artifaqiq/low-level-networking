#!/usr/bin/env python

import sys, threading, socket, struct

LOCK = threading.Lock()

IPS_REQUEST = 'IP_REQUEST'
IPS_REPLY_PREFIX = 'MY_HOSTNAME'


def log(text):
    with LOCK:
        print('[' + threading.current_thread().getName() + '] ' + text)


class AbstractSender(threading.Thread):
    def __init__(self, group_ip, group_port=3000):
        super(AbstractSender, self).__init__()

        self.group_ip = group_ip
        self.group_port = group_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.configure()

    def configure(self):
        pass

    def run(self):
        super(AbstractSender, self).run()
        self._do_sending()

    def _do_sending(self):
        log("Ready to sending to group {}".format(self.group_ip))
        while True:
            try:
                message = raw_input()
                if message == 'ips':
                    self.sock.sendto(IPS_REQUEST, (self.group_ip, self.group_port))
                    continue
                self.sock.sendto(message, (self.group_ip, self.group_port))
            except Exception as e:
                if self.sock:
                    self.sock.close()


class AbstractReceiver(threading.Thread):
    def __init__(self, group_ip, self_ip='0.0.0.0', self_port=3000, group_port=3000):
        super(AbstractReceiver, self).__init__()

        self.group_port = group_port
        self.group_ip = group_ip
        self.self_ip = self_ip
        self.self_port = self_port

        self.sock = None

        self.configure()

    def configure(self):
        pass

    def run(self):
        super(AbstractReceiver, self).run()
        self._do_receive()

    def _do_receive(self):
        log("Start receiving group {}".format(self.group_ip))
        while True:
            try:
                message, address = self.sock.recvfrom(255)
                if message == IPS_REQUEST:
                    self._do_send_ip(address[0])
                elif IPS_REPLY_PREFIX in message:
                    if message.split(":")[1] == socket.gethostbyname(socket.gethostname()):
                        hostname = message.split(':')[2]
                        print "+1. {} [{}]".format(hostname, address[0])
                else:
                    print "[{}]: {}".format(address[0], message)
            except Exception as e:
                if self.sock:
                    self.sock.close()

    def _do_send_ip(self, host):
        self.sock.sendto(IPS_REPLY_PREFIX + ":" + host + ":" + socket.gethostname(), (self.group_ip, self.group_port))


class MulticastReceiver(AbstractReceiver):
    def __init__(self, group_ip, self_ip='0.0.0.0', self_port=3000, group_port=3000):
        super(MulticastReceiver, self).__init__(group_ip, self_ip=self_ip, self_port=self_port, group_port=group_port)

    def configure(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        membership = socket.inet_aton(self.group_ip) + socket.inet_aton(socket.gethostbyname(socket.gethostname()))

        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.sock.bind((self.self_ip, self.self_port))


class MulticastSender(AbstractSender):
    def __init__(self, group_ip, group_port=3000):
        super(MulticastSender, self).__init__(group_ip, group_port=group_port)

    def configure(self):
        ttl = struct.pack('b', 1)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


class BroadcastReceiver(AbstractReceiver):
    def __init__(self, group_ip, self_ip='0.0.0.0', self_port=3000, group_port=3000):
        super(BroadcastReceiver, self).__init__(group_ip, self_ip=self_ip, self_port=self_port, group_port=group_port)

    def configure(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.self_ip, self.self_port))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)


class BroadcastSender(AbstractSender):
    def __init__(self, group_ip, group_port=3000):
        super(BroadcastSender, self).__init__(group_ip, group_port=group_port)

    def configure(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', 0))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)


if __name__ == "__main__":
    assert len(sys.argv) == 2
    group_ip = sys.argv[1]

    if group_ip == '255.255.255.255':
        print "Using broadcast "
        receiver = BroadcastReceiver(group_ip)
        sender = BroadcastSender(group_ip)
    else:
        print "Using multicast"
        receiver = MulticastReceiver(group_ip)
        sender = MulticastSender(group_ip)

    receiver.setDaemon(True)
    sender.setDaemon(True)

    receiver.start()
    sender.start()

    receiver.join()
    receiver.join()
