
from scapy.all import *
from scapy.layers.inet import IPv6,UDP,IPv6ExtHdrSegmentRouting

import twamp
import time


i=IPv6() 
i.src="fcff:2::1"
i.dst="fcff:3::1" 

r = IPv6ExtHdrSegmentRouting()
r.addresses = ['fcff:5::100', 'fcff:4::1', 'fcff:3::1']
r.segleft = 2
r.lastentry = 2 
r.autopad = 1 
r.display() 

i2 = IPv6()
i2.src = "fcff:2::1"
i2.dst = "fcff:6::1"

q=UDP(dport=123)



t = twamp.TWAMPTestQuery(SequenceNumber=1, 
                                TransmitCounter=2,
                                BlockNumber=3,
                                SenderControlCode=1)

pkt=(i/r/i2/q/t)

send(pkt)


