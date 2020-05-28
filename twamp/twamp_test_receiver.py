#!/usr/bin/python

from scapy.all import *
from scapy.layers.inet import IP,UDP
from scapy.layers.inet6 import IPv6,IPv6ExtHdrSegmentRouting

import twamp

def rcv(packet):
    print("Packets Recv Callback")
    if UDP in packet:
        if packet[UDP].dport==1205:
            packet[UDP].decode_payload_as(twamp.TWAMPTestQuery)
            print(packet.show())
            hexdump(packet[twamp.TWAMPTestQuery])
        else:
            print(packet.show())

sniff(iface="veth-c2", filter="ip6", prn=rcv)

