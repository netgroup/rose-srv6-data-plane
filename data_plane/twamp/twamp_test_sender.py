
from scapy.all import *
from scapy.layers.inet import IP,UDP

from scapy.layers.inet6 import IPv6,IPv6ExtHdrSegmentRouting
import twamp
import time


mod_sidlist = ['fcff:8::200', 'fcff:4::1', 'fcff:3::1']

i=IPv6() 
i.src="fcff:2::1"
i.dst= mod_sidlist[-1]


r = IPv6ExtHdrSegmentRouting()
r.addresses = mod_sidlist
r.segleft = len(mod_sidlist)-1  #TODO vedere se funziona con NS variabile
r.lastentry = len(mod_sidlist)-1  #TODO vedere se funziona con NS variabile
r.autopad = 1 
r.display() 

i2 = IPv6()
i2.src = "fcff:2::1"
i2.dst = "fcff:6::1"

q=UDP()
q.dport = 1205 #TODO  me li da il controller?
q.sport = 1206 #TODO  me li da il controller?



t = twamp.TWAMPTestQuery(SequenceNumber=1, 
                                TransmitCounter=2,
                                BlockNumber=3,
                                SenderControlCode=1)

pkt=(i/r/i2/q/t)

send(pkt,count=1)


