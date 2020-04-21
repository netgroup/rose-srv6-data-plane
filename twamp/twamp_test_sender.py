
from scapy.all import *
from scapy.layers.inet import IP,UDP

import twamp
import time



query = twamp.TWAMPTestQuery(SequenceNumber=1, 
                                TransmitCounter=2,
                                BlockNumber=3,
                                SenderControlCode=1)

pkt = IP(dst="10.1.1.200")/UDP(dport=50050)/query

pkt.show()
hexdump(query)
send(pkt)


