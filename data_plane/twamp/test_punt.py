from scapy.all import * 


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
d=Raw(load="#53abc")
p=(i/r/i2/q/d)
send(p,iface="veth3")

#send(IPv6(dst="fcff:3::1")/UDP(dport=123)/Raw(load="abc"))
