from scapy.all import *

import twamp

def rcv(packet):
    print("Packets Recv Callback")
    packet[UDP].decode_payload_as(twamp.TWAMPTestQuery)
    print(packet.show())
    hexdump(packet[twamp.TWAMPTestQuery])

sniff(iface="ctrl0", filter="udp and port 50050", prn=rcv)

