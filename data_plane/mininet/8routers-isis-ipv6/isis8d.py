#!/usr/bin/python

import os
import shutil
from ipaddress import IPv6Network
from mininet.topo import Topo
from mininet.node import Host, OVSBridge
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.util import dumpNodeConnections
from mininet.link import Link
from mininet.log import setLogLevel

#BASEDIR = "/home/user/mytests/ospf3routers/nodeconf/"
BASEDIR = os.getcwd()+"/nodeconf/"
OUTPUT_PID_TABLE_FILE = "/tmp/pid_table_file.txt"

PRIVDIR = '/var/priv'


# Allocates mgmt address
class MgmtAllocator(object):

  bit = 64
  net = unicode("2000::/%d" % bit)
  prefix = 64

  def __init__(self): 
    print "*** Calculating Available Mgmt Addresses"
    self.mgmtnet = (IPv6Network(self.net)).hosts()
  
  def nextMgmtAddress(self):
    n_host = next(self.mgmtnet)
    return n_host.__str__()

class BaseNode(Host):

    def __init__(self, name, *args, **kwargs):
        dirs = [PRIVDIR]
        Host.__init__(self, name, privateDirs=dirs, *args, **kwargs)
        self.dir = "/tmp/%s" % name
        self.nets = []
        if not os.path.exists(self.dir):
            os.makedirs(self.dir) 

    def config(self, **kwargs):
        # Init steps
        Host.config(self, **kwargs)
        # Iterate over the interfaces
        first = True
        for intf in self.intfs.itervalues():
            # Remove any configured address
            self.cmd('ifconfig %s 0' %intf.name)
            # # For the first one, let's configure the mgmt address
            if first:
               first = False
               self.cmd('ip a a %s dev %s' %(kwargs['mgmtip'], intf.name))
        #let's write the hostname in /var/mininet/hostname
        self.cmd("echo '" + self.name + "' > "+PRIVDIR+"/hostname")
        if os.path.isfile(BASEDIR+self.name+"/start.sh") :
            self.cmdPrint('source %s' %BASEDIR+self.name+"/start.sh")

    def cleanup(self):
        def remove_if_exists (filename):
            if os.path.exists(filename):
                os.remove(filename)

        Host.cleanup(self)
        # Rm dir
        if os.path.exists(self.dir):
            shutil.rmtree(self.dir)

        remove_if_exists(BASEDIR+self.name+"/zebra.pid")
        remove_if_exists(BASEDIR+self.name+"/zebra.log")
        remove_if_exists(BASEDIR+self.name+"/zebra.sock")
        remove_if_exists(BASEDIR+self.name+"/isis8d.pid")
        remove_if_exists(BASEDIR+self.name+"/isis8d.log")
        remove_if_exists(BASEDIR+self.name+"/isisd.log")
        remove_if_exists(BASEDIR+self.name+"/isisd.pid")

        remove_if_exists(OUTPUT_PID_TABLE_FILE)

        # if os.path.exists(BASEDIR+self.name+"/zebra.pid"):
        #     os.remove(BASEDIR+self.name+"/zebra.pid")

        # if os.path.exists(BASEDIR+self.name+"/zebra.log"):
        #     os.remove(BASEDIR+self.name+"/zebra.log")

        # if os.path.exists(BASEDIR+self.name+"/zebra.sock"):
        #     os.remove(BASEDIR+self.name+"/zebra.sock")

        # if os.path.exists(BASEDIR+self.name+"/ospfd.pid"):
        #     os.remove(BASEDIR+self.name+"/ospfd.pid")

        # if os.path.exists(BASEDIR+self.name+"/ospfd.log"):
        #     os.remove(BASEDIR+self.name+"/ospfd.log")

        # if os.path.exists(OUTPUT_PID_TABLE_FILE):
        #     os.remove(OUTPUT_PID_TABLE_FILE)


class Router(BaseNode):
    def __init__(self, name, *args, **kwargs):
        BaseNode.__init__(self, name, *args, **kwargs)

# the add_link function creates a link and assigns the interface names
# as node1-node2 and node2-node1
def add_link (node1, node2, assign_names=True):
    if assign_names:
        Link(node1, node2, intfName1=node1.name+'-'+node2.name,
                        intfName2=node2.name+'-'+node1.name)
    else:
        Link(node1, node2)

def create_topo(my_net):
    allocator = MgmtAllocator()

    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    h11 = my_net.addHost(name='h11', cls=BaseNode, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    h12 = my_net.addHost(name='h12', cls=BaseNode, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    h13 = my_net.addHost(name='h13', cls=BaseNode, mgmtip=mgmtip)

    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    h31 = my_net.addHost(name='h31', cls=BaseNode, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    h32 = my_net.addHost(name='h32', cls=BaseNode, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    h33 = my_net.addHost(name='h33', cls=BaseNode, mgmtip=mgmtip)

    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    h51 = my_net.addHost(name='h51', cls=BaseNode, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    h52 = my_net.addHost(name='h52', cls=BaseNode, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    h53 = my_net.addHost(name='h53', cls=BaseNode, mgmtip=mgmtip)

    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    h81 = my_net.addHost(name='h81', cls=BaseNode, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    h82 = my_net.addHost(name='h82', cls=BaseNode, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    h83 = my_net.addHost(name='h83', cls=BaseNode, mgmtip=mgmtip)

    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    r1 = my_net.addHost(name='r1', cls=Router, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    r2 = my_net.addHost(name='r2', cls=Router, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    r3 = my_net.addHost(name='r3', cls=Router, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    r4 = my_net.addHost(name='r4', cls=Router, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    r5 = my_net.addHost(name='r5', cls=Router, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    r6 = my_net.addHost(name='r6', cls=Router, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    r7 = my_net.addHost(name='r7', cls=Router, mgmtip=mgmtip)
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    r8 = my_net.addHost(name='r8', cls=Router, mgmtip=mgmtip)

    #note that if the interface names are not provided,
    #the order of adding link will determine the
    #naming of the interfaces (e.g. on r1: r1-eth0, r1-eth1, r1-eth2...)
    # it is possible to provide names as follows
    # Link(h1, r1, intfName1='h1-eth0', intfName2='r1-eth0')
    # the add_link function creates a link and assigns the interface names
    # as node1-node2 and node2-node1

    # Create the mgmt switch
    br_mgmt = my_net.addSwitch(name='br-mgmt1', cls=OVSBridge)
    # Mgmt name
    mgmt = 'mgmt'
    # IP of the management station
    mgmtip = "%s/%s" % (allocator.nextMgmtAddress(), MgmtAllocator.prefix)
    # Create the mgmt node in the root namespace
    mgmt = my_net.addHost(name=mgmt, cls=BaseNode, sshd=False, inNamespace=False, mgmtip=mgmtip)
    # Create a link between mgmt switch and mgmt station
    add_link(mgmt, br_mgmt, False)
    # Connect all the routers to the management network
    for host in my_net.hosts:
        if host.inNamespace:
            add_link(host, br_mgmt, False)

    #hosts of r1
    add_link(h11,r1)
    add_link(h12,r1)
    add_link(h13,r1)
    #r1 - r2
    add_link(r1,r2)
    #r2 - r3
    add_link(r2,r3)
    #r2 - r7
    add_link(r2,r7)
    #hosts of r3
    add_link(h31,r3)
    add_link(h32,r3)
    add_link(h33,r3)
    #r3 - r4
    add_link(r3,r4)
    #r4 - r5
    add_link(r4,r5)
    #r4 - r6
    add_link(r4,r6)
    #hosts of r5
    add_link(h51,r5)
    add_link(h52,r5)
    add_link(h53,r5)
    #r5 - r6
    add_link(r5,r6)
    #r6 - r7
    add_link(r6,r7)
    #r6 - r8
    add_link(r6,r8)
    #r7 - r8
    add_link(r7,r8)
    #hosts of r8
    add_link(h81,r8)
    add_link(h82,r8)
    add_link(h83,r8)

def stopAll():
    # Clean Mininet emulation environment
    os.system('sudo mn -c')
    # Kill all the started daemons
    os.system('sudo killall zebra isisd')

def extractHostPid (dumpline):
    temp = dumpline[dumpline.find('pid=')+4:]
    return int(temp [:len(temp)-2])


    
def simpleTest():
    "Create and test a simple network"

    #topo = RoutersTopo()
    #net = Mininet(topo=topo, build=False, controller=None)
    net = Mininet(topo=None, build=False, controller=None, ipBase='172.16.0.0/12')
    create_topo(net)

    net.build()
    net.start()


    dumpNodeConnections(net.hosts)
    #print "Testing network connectivity"
    #net.pingAll()

    with open(OUTPUT_PID_TABLE_FILE,"w") as file:
        for host in net.hosts:
            file.write("%s %d\n" % (host, extractHostPid( repr(host) )) )

    CLI( net ) 
    net.stop() 
    stopAll()



if __name__ == '__main__':
    # Tell mininet to print useful information
    setLogLevel('info')
    simpleTest()
