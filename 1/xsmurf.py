#!/usr/bin/env python
import socket, sys
from impacket import ImpactDecoder, ImpactPacket

src = sys.argv[1]
dst = sys.argv[2]

ip = ImpactPacket.IP()
ip.set_ip_src(src)
ip.set_ip_dst(dst)

icmp = ImpactPacket.ICMP()
icmp.set_icmp_type(icmp.ICMP_ECHO)

icmp.contains(ImpactPacket.Data("a" * 100))
ip.contains(icmp)

s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)


icmp.set_icmp_id(1)
icmp.set_icmp_cksum(0)
icmp.auto_checksum = 0

s.sendto(ip.get_packet(), (dst, 0))