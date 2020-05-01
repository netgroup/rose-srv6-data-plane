#!/usr/bin/python

from concurrent import futures
import grpc
import logging
from threading import Thread
import sched
import time
from datetime import datetime, timedelta

import subprocess
import shlex
import pprint

from scapy.all import *
from scapy.layers.inet import IP,UDP
from scapy.layers.inet6 import IPv6,IPv6ExtHdrSegmentRouting
import twamp


# FRPC protocol
import srv6pmCommons_pb2_grpc
import srv6pmCommons_pb2
import srv6pmService_pb2_grpc
import srv6pmService_pb2
import srv6pmReflector_pb2
import srv6pmReflector_pb2_grpc
import srv6pmSender_pb2
import srv6pmSender_pb2_grpc

from xdp_srv6_pfplm_helper_user import EbpfException, EbpfPFPLM

class EbpfInterf():
    def __init__(self,outInterface,inInterface):
        self.outInterface = outInterface
        self.inInterface = inInterface
        self.BLUE=1
        self.RED=0
        try:
            self.inDriver = EbpfPFPLM()
            self.inDriver.pfplm_load(self.outInterface, self.inDriver.lib.XDP_PROG_DIR_EGRESS, self.inDriver.lib.F_VERBOSE | self.inDriver.lib.F_FORCE)
            self.inDriver.pfplm_change_active_color(self.outInterface, self.BLUE)
        except EbpfException as e:
            e.print_exception()

    def set_sidlist(self,sid_list):
        print("EBPF INS sidlist",sid_list)
        try:
            self.inDriver.pfplm_add_flow(self.outInterface, sid_list) #da testare
        except EbpfException as e:
            e.print_exception()
    def rem_sidlist(self,sid_list):
        print("EBPF REM sidlist",sid_list)
        try:
            self.inDriver.pfplm_del_flow(self.outInterface, sid_list)  #da testare
        except EbpfException as e:
            e.print_exception()
    
    def set_color(self,color):
        if(color==self.BLUE):
            self.inDriver.pfplm_change_active_color(self.outInterface, self.BLUE)
        else:
            self.inDriver.pfplm_change_active_color(self.outInterface, self.RED)

    def read_tx_counter(self,color, segments):
        return self.inDriver.pfplm_get_flow_stats(self.outInterface,segments, color)

    def read_rx_counter(self,color, segments):
        pass

class IpSetInterf():
    def __init__(self):
        self.interface = ""
        self.BLUE=1
        self.RED=0
        self.state = self.BLUE # base conf use blue queue
    
    def sid_list_converter(self,sid_list):
        return " ".join(sid_list)

    def set_sidlist(self,sid_list):
        ipset_sid_list = self.sid_list_converter(sid_list)
        print("IPSET new sidlist",ipset_sid_list)

    def rem_sidlist(self,sid_list):
        ipset_sid_list = self.sid_list_converter(sid_list)
        print("IPSET rem sidlist",ipset_sid_list)

    def set_color(self,color):
        if(self.state==color): #no need to change
            return
        if(color==self.BLUE):
            self.set_blue_queue()
            self.state = self.BLUE
        else:
            self.set_red_queue()
            self.state = self.RED
    
    def set_red_queue(self):             
        print('IPSET RED QUEUE')
        cmd = "ip6tables -D POSTROUTING -t mangle -m rt --rt-type 4 -j blue-out"
        shlex.split(cmd)
        result = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True)

    def set_blue_queue(self):
        print('IPSET BLUE QUEUE')
        cmd = "ip6tables -I POSTROUTING 1 -t mangle -m rt --rt-type 4 -j blue-out"
        shlex.split(cmd)
        result = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True)

    def read_tx_counter(self,color, sid_list):
        ipset_sid_list = self.sid_list_converter(sid_list)
        queue_name = self.get_queue_name(color,"out")
        print('IPSET READ TX COUNTER', color, ipset_sid_list,queue_name)
        result = subprocess.run(['ipset', 'list',queue_name], stdout=subprocess.PIPE)
        res_arr = result.stdout.decode('utf-8').splitlines()

        counter = {}
        if not res_arr[0].startswith("Name:"):
            raise Exception('Queue not present')

        for line in res_arr:
            if line.startswith("segs"):
                sidlist = line[line.find("[") + 2:line.find("]") - 1]
                if sidlist == ipset_sid_list:
                    cnt = line[line.find("packets") + 8:line.find("bytes") - 1]
                    return int(cnt)

        raise Exception('SID list not present')

    def read_rx_counter(self,color, sid_list):
        ipset_sid_list = self.sid_list_converter(sid_list)
        queue_name = self.get_queue_name(color,"in")
        print('IPSET READ RX COUNTER', color, ipset_sid_list,queue_name)
        result = subprocess.run(['ipset', 'list',queue_name], stdout=subprocess.PIPE)
        res_arr = result.stdout.decode('utf-8').splitlines();

        counter = {}
        if not res_arr[0].startswith("Name:"):
            raise Exception('Queue not present')

        for line in res_arr:
            if line.startswith("segs"):
                sidlist = line[line.find("[") + 2:line.find("]") - 1]
                if sidlist == ipset_sid_list:
                    cnt = line[line.find("packets") + 8:line.find("bytes") - 1]
                    return int(cnt)

        raise Exception('SID list not present')
    
    def get_queue_name(self,color,direction):
        if(color==self.BLUE):
            return 'blue-ht-'+direction
        else:
            return 'red-ht-'+direction



class TestPacketReceiver(Thread):
    def __init__(self, interface, sender, reflector ):
        Thread.__init__(self) 
        self.interface = interface
        self.SessionSender = sender
        self.SessionReflector = reflector

    def packetRecvCallback(self, packet):
        if UDP in packet:
            if packet[UDP].dport==1205:
                packet[UDP].decode_payload_as(twamp.TWAMPTestQuery)
                print(packet.show())
                self.SessionReflector.recvTWAMPTestQuery(packet)
            elif packet[UDP].dport==1206:
                packet[UDP].decode_payload_as(twamp.TWAMPTestResponse)
                print(packet.show())
                self.SessionSender.recvTWAMPResponse(packet)
            else:
                print(packet.show())
    
    def run(self):
        print("TestPacketReceiver Start sniffing...")
        sniff(iface=self.interface, filter="ip6", prn=self.packetRecvCallback)
        print("TestPacketReceiver Stop sniffing")
        # codice netqueue




class SessionSender(Thread):
    def __init__(self,driver):
        Thread.__init__(self)
        self.startedMeas = False
        self.monitored_path = {}

        # self.lock = Thread.Lock()

        self.interval = 10
        self.margin = timedelta(milliseconds=3000)
        self.numColor = 2
        self.hwadapter = driver
        self.scheduler = sched.scheduler(time.time, time.sleep)
        # self.startMeas("fcff:3::1/fcff:4::1/fcff:5::1","25") #for test

    ''' Thread Tasks'''

    def run(self):
        #enter(delay, priority, action, argument=(), kwargs={})
        print("SessionSender start")
        # Starting changeColor task
        ccTime =time.mktime(self.getNexttimeToChangeColor().timetuple())
        self.scheduler.enterabs(ccTime, 1, self.runChangeColor)
        # Starting measure task
        dmTime =time.mktime(self.getNexttimeToMeasure().timetuple())
        self.scheduler.enterabs(dmTime, 1, self.runMeasure)
        self.scheduler.run()
        print("SessionSender stop")

    def runChangeColor(self):
        if self.startedMeas:
            print(datetime.now(),"SS runChangeColor meas:",self.startedMeas)
            color = self.getColor()
            self.hwadapter.set_color(color)
        
        ccTime =time.mktime(self.getNexttimeToChangeColor().timetuple())
        self.scheduler.enterabs(ccTime, 1, self.runChangeColor)


    def runMeasure(self):
        if self.startedMeas:                
            print(datetime.now(),"SS runMeasure meas:",self.startedMeas)
            print("Exec Measure")
            self.sendTWAMPTestQuery()

        # Schedule next measure 
        dmTime =time.mktime(self.getNexttimeToMeasure().timetuple())
        self.scheduler.enterabs(dmTime, 1, self.runMeasure)

    ''' TWAMP methods '''

    def sendTWAMPTestQuery(self):
        print("sendTWAMPTestQuery")
        prevcolor = self.getPrevColor()
        txcounter = self.hwadapter.read_tx_counter(prevcolor,self.monitored_path["sidlist"])
        print("TX counter: ",txcounter)
        

        ipv6_packet = IPv6()
        ipv6_packet.src = "fcff:2::1"
        ipv6_packet.dst = "fcff:3::1"

        mod_sidlist = self.set_punt(list(self.monitored_path["sidlistrev"]))
        print("sending to:",mod_sidlist)

        ipv6_packet_inside = IPv6()
        ipv6_packet_inside.src = "fcff:2::1"
        ipv6_packet_inside.dst = "fcff:5::1"

        udp_packet = UDP()
        udp_packet.dport = 1205
        udp_packet.sport = 1206
    
    
        twamp_data = twamp.TWAMPTestQuery(SequenceNumber=1, 
                                TransmitCounter=txcounter,
                                BlockNumber=prevcolor,
                                SenderControlCode=1)

        pkt = ipv6_packet / IPv6ExtHdrSegmentRouting(addresses=mod_sidlist, segleft=2,
                                                    lastentry=2) / ipv6_packet_inside / udp_packet / twamp_data
        
        scapy.all.send(pkt, count=1, verbose=False)


    def recvTWAMPResponse(self,packet):
        print("recvTWAMPResponse")
        pass

    ''' Interface for the controller'''
    def startMeas(self, sidList,meas_id):
        if self.startedMeas:
            return -1 # already started
        print("CTRL: Start Meas for "+sidList)
        self.monitored_path["sidlistgrpc"] = sidList
        self.monitored_path["sidlist"] = sidList.split("/")
        self.monitored_path["sidlistrev"] = self.monitored_path["sidlist"][::-1]
        self.monitored_path["meas_counter"] = 0 #reset counter
        self.monitored_path["meas_id"] = meas_id
        self.monitored_path['lastMeas'] = -1
        pprint.pprint(self.monitored_path)
        self.hwadapter.set_sidlist(self.monitored_path["sidlist"])
        self.startedMeas = True
        return 1 

    def stopMeas(self, sidList):
        print("CTRL: Stop Meas for "+sidList)
        self.startedMeas = False
        self.hwadapter.rem_sidlist(self.monitored_path["sidlist"])
        self.monitored_path={}
        return 1 #mettere in un try e semmay tronare errore


    def getMeas(self, sidList):
        print("CTRL: Get Mead Data for "+sidList)
        return self.monitored_path['lastMeas']


    ''' Utility methods '''

    def getNexttimeToChangeColor(self):
        date = datetime.now()
        date_timestamp = date.timestamp()
        num_interval = math.ceil(date_timestamp / self.interval)
        return datetime.fromtimestamp(num_interval * self.interval)

    def getNexttimeToMeasure(self):
        date = self.getNexttimeToChangeColor() + self.margin
        return date

    def getColor(self):
        date = datetime.now()
        date_timestamp = date.timestamp()
        num_interval = math.ceil(date_timestamp / self.interval)
        return num_interval % self.numColor

    def getPrevColor(self):
        date = datetime.now()
        date_timestamp = date.timestamp()
        num_interval = math.ceil(date_timestamp / self.interval)
        return (num_interval-1) % self.numColor

    def set_punt(self,list):
        mod_list = list
        mod_list[0]=mod_list[0]+"00"
        return mod_list

    def rem_punt(self,list):
        mod_list = list
        mod_list[0]=mod_list[0][:-2]
        return mod_list



''' ***************************************** REFLECTOR '''

class SessionReflector(Thread):
    def __init__(self,driver):
        Thread.__init__(self)
        self.name = "SessionReflector"
        self.startedMeas = False
        self.interval = 10
        self.margin = timedelta(milliseconds=3000)
        self.numColor = 2

        self.monitored_path = {}

        self.hwadapter = driver

        # per ora non lo uso è per il cambio di colore
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def run(self):
        #enter(delay, priority, action, argument=(), kwargs={})
        print("SessionReflector start")
        # Starting changeColor task
        ccTime =time.mktime(self.getNexttimeToChangeColor().timetuple())
        self.scheduler.enterabs(ccTime, 1, self.runChangeColor)
        self.scheduler.run()
        print("SessionReflector stop")


    def runChangeColor(self):
        if self.startedMeas:
            print(datetime.now(),"RF runChangeColor meas:",self.startedMeas)
            color = self.getColor()
            self.hwadapter.set_color(color)
        
        ccTime =time.mktime(self.getNexttimeToChangeColor().timetuple())
        self.scheduler.enterabs(ccTime, 1, self.runChangeColor)

    ''' TWAMP methods '''

    def sendTWAMPTestResponse(self, sid_list, block_color, sender_counter):
        print("sendTWAMPTestResponse")
        
        print(sid_list)
        nop_sid_list = self.rem_punt(sid_list)[::-1]
        print(nop_sid_list)
        print(block_color)
        rxcounter = self.hwadapter.read_rx_counter(block_color,nop_sid_list)

        # reverse sidlist
        prevcolor = self.getPrevColor()
        txcounter = self.hwadapter.read_tx_counter(prevcolor,self.monitored_path["returnsidlist"])
        print("TX counter: ",txcounter)
        

        ipv6_packet = IPv6()
        ipv6_packet.src = "fcff:5::1"
        ipv6_packet.dst = "fcff:4::1"

        mod_sidlist = self.set_punt(list(self.monitored_path["returnsidlistrev"]))
        print("sending to:",mod_sidlist)

        ipv6_packet_inside = IPv6()
        ipv6_packet_inside.src = "fcff:5::1"
        ipv6_packet_inside.dst = "fcff:2::1"

        udp_packet = UDP()
        udp_packet.dport = 1206
        udp_packet.sport = 1205
    
    
        twamp_data = twamp.TWAMPTestResponse(SequenceNumber=1, 
                                TransmitCounter=txcounter,
                                BlockNumber=prevcolor,
                                ReceiveCounter=rxcounter,
                                SenderCounter=sender_counter,
                                SenderBlockNumber=block_color,
                                ReceverControlCode=0)

        pkt = ipv6_packet / IPv6ExtHdrSegmentRouting(addresses=mod_sidlist, segleft=2,
                                                    lastentry=2) / ipv6_packet_inside / udp_packet / twamp_data
        
        scapy.all.send(pkt, count=1, verbose=False)        
        pass

    def recvTWAMPTestQuery(self,packet):
        srh = packet[IPv6ExtHdrSegmentRouting]
        sid_list = srh.addresses
        query = packet[twamp.TWAMPTestQuery]
        self.sendTWAMPTestResponse(sid_list, query.BlockNumber, query.TransmitCounter)

    ''' Interface for the controller'''

    def startMeas(self, sidList,retList):
        print("CTRL REFL: Start Meas for "+sidList)
        if self.startedMeas:
            return -1 # already started
        print("CTRL: Start Meas for "+sidList)
        self.monitored_path["sidlistgrpc"] = sidList
        self.monitored_path["sidlist"] = sidList.split("/")
        self.monitored_path["sidlistrev"] = self.monitored_path["sidlist"][::-1]
        self.monitored_path["returnsidlist"] = retList.split("/")   
        self.monitored_path["returnsidlistrev"] = self.monitored_path["returnsidlist"][::-1]
        pprint.pprint(self.monitored_path)
        self.hwadapter.set_sidlist(self.monitored_path["returnsidlist"])
        self.startedMeas = True

    def stopMeas(self, sidList):
        print("CTRL REFL: Stop Meas for "+sidList)
        self.startedMeas = False
        self.hwadapter.rem_sidlist(self.monitored_path["sidlist"])
        self.monitored_path={}
        return 1 #mettere in un try e semmai tornare errore



    ''' Utility methods '''

    def getNexttimeToChangeColor(self):
        date = datetime.now()
        date_timestamp = date.timestamp()
        num_interval = math.ceil(date_timestamp / self.interval)
        return datetime.fromtimestamp(num_interval * self.interval)

    def getNexttimeToMeasure(self):
        date = self.getNexttimeToChangeColor() + self.margin
        return date

    def getColor(self):
        date = datetime.now()
        date_timestamp = date.timestamp()
        num_interval = math.ceil(date_timestamp / self.interval)
        return num_interval % self.numColor

    def getPrevColor(self):
        date = datetime.now()
        date_timestamp = date.timestamp()
        num_interval = math.ceil(date_timestamp / self.interval)
        return (num_interval-1) % self.numColor

    def set_punt(self,list):
        mod_list = list
        mod_list[0]=mod_list[0]+"00"
        return mod_list

    def rem_punt(self,list):
        mod_list = list
        mod_list[0]=mod_list[0][:-2]
        return mod_list




class TWAMPController(srv6pmService_pb2_grpc.SRv6PMServicer):
    def __init__(self, SessionSender,SessionReflector): 
        self.port_server = 20000 
        self.sender = SessionSender
        self.reflector = SessionReflector

    def startExperimentSender(self, request, context):
        print("REQ - startExperimentSender")
        res = self.sender.startMeas(request.sdlist,"1234")
        return srv6pmSender_pb2.StartExperimentSenderReply(status=res)

    def stopExperimentSender(self, request, context):
        print("REQ - stopExperimentSender")
        self.sender.stopMeas(request.sdlist)
        res = 1
        return srv6pmCommons_pb2.StopExperimentReply(status=res)

    def startExperimentReflector(self, request, context):
        print("REQ - startExperimentReflector")
        self.reflector.startMeas(request.sdlist,"fcff:4::1/fcff:3::1/fcff:2::1")
        return srv6pmReflector_pb2.StartExperimentReflectorReply(status=1)

    def stopExperimentReflector(self, request, context):
        print("REQ - startExperimentReflector")
        self.reflector.stopMeas(request.sdlist)
        res = 1
        return srv6pmCommons_pb2.StopExperimentReply(status=1)

    def retriveExperimentResults(self, request, context):
        print("REQ - retriveExperimentResults")
        res = self.sender.getMeas(request.sdlist)
        return srv6pmCommons_pb2.ExperimentDataResponse(status=res)


def serve(ipaddr,gprcPort,recvInterf,epbfOutInterf,epbfInInterf):
    #driver = EbpfInterf(epbfOutInterf,epbfInInterf)
    driver = IpSetInterf()

    sessionsender = SessionSender(driver)
    sessionreflector = SessionReflector(driver)
    packetRecv = TestPacketReceiver(recvInterf,sessionsender,sessionreflector)
    sessionreflector.start()
    sessionsender.start()
    packetRecv.start()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    srv6pmService_pb2_grpc.add_SRv6PMServicer_to_server(TWAMPController(sessionsender,sessionreflector), server)
    server.add_insecure_port("{ip}:{port}".format(ip=ipaddr,port=gprcPort))
    print("\n-------------- Start Demon --------------\n")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    ipaddr =  sys.argv[1]
    gprcPort =  sys.argv[2]
    nodeID =  sys.argv[3]
    if nodeID=="2":
        recvInterf = "veth-punt1"
        epbfOutInterf = "veth3-egr"
        epbfInInterf = "veth3"
    elif nodeID=="5":
        recvInterf = "veth-punt2"
        epbfOutInterf = "veth8-egr"
        epbfInInterf = "veth8"
    else:
        exit(-1)

    logging.basicConfig()
    serve(ipaddr,gprcPort,recvInterf,epbfOutInterf,epbfInInterf)
