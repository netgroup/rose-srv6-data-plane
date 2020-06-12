#!/usr/bin/python

from srv6_pfplm_helper_user import EbpfException, EbpfPFPLM
import os
import sys
from threading import Thread
import sched
import time
from datetime import datetime, timedelta
import math

import subprocess
import shlex

from scapy.all import send, sniff
from scapy.layers.inet import UDP
from scapy.layers.inet6 import IPv6, IPv6ExtHdrSegmentRouting
from data_plane.twamp import twamp

import netifaces

# Folder containing this script
BASE_PATH = os.path.dirname(os.path.realpath(__file__))

# SRv6 PFPLM dependencies
SRV6_PM_XDP_EBPF_PATH = os.getenv('SRV6_PM_XDP_EBPF_PATH', None)
if SRV6_PM_XDP_EBPF_PATH is None:
    print('SRV6_PM_XDP_EBPF_PATH environment variable not set')
    exit(-2)
SRV6_PFPLM_PATH = os.path.join(SRV6_PM_XDP_EBPF_PATH, 'srv6-pfplm/')

# sys.path.append(SRV6_PFPLM_PATH)


''' ***************************************** DRIVER EBPF '''


class EbpfInterf():
    def __init__(self, in_interfaces=[], out_interfaces=[]):
        if len(in_interfaces) == 0:
            in_interfaces = netifaces.interfaces()
        if len(out_interfaces) == 0:
            out_interfaces = netifaces.interfaces()

        self.BLUE = 1
        self.RED = 0
        self.mark = [1, 2]
        self.epbfInterfsEgr = out_interfaces
        self.epbfInterfsIng = in_interfaces

        try:
            self.epbf = EbpfPFPLM()
            self.EGR = self.epbf.lib.FLOW_DIR_EGRESS
            self.ING = self.epbf.lib.FLOW_DIR_INGRESS

            for intf in in_interfaces:
                try:
                    self.epbf.load_ingress(intf)
                except EbpfException as e:
                    e.print_exception()
            for intf in out_interfaces:
                try:
                    self.epbf.load_egress(intf)
                except EbpfException as e:
                    e.print_exception()

            self.epbf.pfplm_change_active_color(self.mark[self.BLUE])

        except EbpfException as e:
            e.print_exception()

    def stop(self):
        print('Deallocating EbpfInterf object')
        try:
            for intf in self.epbfInterfsIng:
                try:
                    self.epbf.unload_ingress(intf)
                except EbpfException as e:
                    e.print_exception()
            for intf in self.epbfInterfsEgr:
                try:
                    self.epbf.unload_egress(intf)
                except EbpfException as e:
                    e.print_exception()

        except EbpfException as e:
            e.print_exception()

    def sid_list_converter(self, sid_list):
        return ",".join(sid_list)

    def set_sidlist_out(self, sid_list):
        # if interf not in self.epbfInterfsEgr:
        #     try:
        #         EbpfPFPLM.load_egress(interf)
        #     except EbpfException as e:
        #         e.print_exception()
        #     self.epbfInterfsEgr.append(interf)

        ebpf_sid_list = self.sid_list_converter(sid_list)
        print("EBPF INS OUT sidlist", ebpf_sid_list)
        try:
            self.epbf.pfplm_add_flow(self.EGR, ebpf_sid_list)
        except EbpfException as e:
            e.print_exception()

    def set_sidlist_in(self, sid_list):
        # if interf not in self.epbfInterfsIng:
        #     try:
        #         EbpfPFPLM.load_ingress(interf)
        #     except EbpfException as e:
        #         e.print_exception()
        #     self.epbfInterfsIng.append(interf)

        ebpf_sid_list = self.sid_list_converter(sid_list)
        print("EBPF INS IN sidlist", ebpf_sid_list)
        try:
            self.epbf.pfplm_add_flow(self.ING, ebpf_sid_list)
        except EbpfException as e:
            e.print_exception()

    def rem_sidlist_out(self, sid_list):
        ebpf_sid_list = self.sid_list_converter(sid_list)
        print("EBPF REM sidlist", ebpf_sid_list)
        try:
            self.epbf.pfplm_del_flow(self.EGR, ebpf_sid_list)  # da testare
        except EbpfException as e:
            e.print_exception()

    def rem_sidlist_in(self, sid_list):
        ebpf_sid_list = self.sid_list_converter(sid_list)
        print("EBPF REM sidlist", ebpf_sid_list)
        try:
            self.epbf.pfplm_del_flow(self.ING, ebpf_sid_list)  # da testare
        except EbpfException as e:
            e.print_exception()

    def set_color(self, color):
        if len(self.epbfInterfsEgr) == 0:
            return

        if(color == self.BLUE):
            self.epbf.pfplm_change_active_color(self.mark[self.BLUE])
        else:
            self.epbf.pfplm_change_active_color(self.mark[self.RED])

    def get_color(self):
        if len(self.epbfInterfsEgr) == 0:
            return self.RED
        col = self.epbf.pfplm_get_active_color()
        if col == self.mark[0]:
            return self.RED
        else:
            return self.BLUE
        return -1

    def toggle_color(self):
        if(self.get_color() == self.BLUE):
            self.epbf.pfplm_change_active_color(self.mark[self.RED])
        else:
            self.epbf.pfplm_change_active_color(self.mark[self.BLUE])

    def read_tx_counter(self, color, sid_list):
        ebpf_sid_list = self.sid_list_converter(sid_list)
        print('SID LIST IN READ TX CNT', ebpf_sid_list)
        return self.epbf.pfplm_get_flow_stats(
            self.EGR, ebpf_sid_list, self.mark[color])

    def read_rx_counter(self, color, sid_list):
        ebpf_sid_list = self.sid_list_converter(sid_list)
        return self.epbf.pfplm_get_flow_stats(
            self.ING, ebpf_sid_list, self.mark[color])


''' ***************************************** DRIVER IPSET '''


class IpSetInterf():
    def __init__(self):
        self.interface = ""
        self.BLUE = 1
        self.RED = 0
        self.state = self.BLUE  # base conf use blue queue

    def sid_list_converter(self, sid_list):
        return " ".join(sid_list)

    def set_sidlist(self, sid_list):
        ipset_sid_list = self.sid_list_converter(sid_list)
        # TODO implementare se serve
        # print("IPSET new sidlist",ipset_sid_list)

    def rem_sidlist(self, sid_list):
        ipset_sid_list = self.sid_list_converter(sid_list)
        # TODO implementare se serve
        # print("IPSET rem sidlist",ipset_sid_list)

    def set_color(self, color):
        if(self.state == color):  # no need to change
            return
        if(color == self.BLUE):
            self.set_blue_queue()
            self.state = self.BLUE
        else:
            self.set_red_queue()
            self.state = self.RED

    def set_red_queue(self):
        # print('IPSET RED QUEUE')
        cmd = "ip6tables -D POSTROUTING -t mangle -m rt --rt-type 4 -j blue-out"
        shlex.split(cmd)
        result = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True)

    def set_blue_queue(self):
        # print('IPSET BLUE QUEUE')
        cmd = "ip6tables -I POSTROUTING 1 -t mangle -m rt --rt-type 4 -j blue-out"
        shlex.split(cmd)
        result = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True)

    def read_tx_counter(self, color, sid_list):
        ipset_sid_list = self.sid_list_converter(sid_list)
        queue_name = self.get_queue_name(color, "out")
        # print('IPSET READ TX COUNTER', color, ipset_sid_list,queue_name)
        result = subprocess.run(
            ['ipset', 'list', queue_name], stdout=subprocess.PIPE)
        res_arr = result.stdout.decode('utf-8').splitlines()

        if not res_arr[0].startswith("Name:"):
            raise Exception('Queue not present')

        for line in res_arr:
            if line.startswith("segs"):
                sidlist = line[line.find("[") + 2:line.find("]") - 1]
                if sidlist == ipset_sid_list:
                    cnt = line[line.find("packets") + 8:line.find("bytes") - 1]
                    return int(int(cnt) / 2)

        raise Exception('SID list not present')

    def read_rx_counter(self, color, sid_list):
        ipset_sid_list = self.sid_list_converter(sid_list)
        queue_name = self.get_queue_name(color, "in")
        # print('IPSET READ RX COUNTER', color, ipset_sid_list,queue_name)
        result = subprocess.run(
            ['ipset', 'list', queue_name], stdout=subprocess.PIPE)
        res_arr = result.stdout.decode('utf-8').splitlines()

        if not res_arr[0].startswith("Name:"):
            raise Exception('Queue not present')

        for line in res_arr:
            if line.startswith("segs"):
                sidlist = line[line.find("[") + 2:line.find("]") - 1]
                if sidlist == ipset_sid_list:
                    cnt = line[line.find("packets") + 8:line.find("bytes") - 1]
                    return int(cnt)

        raise Exception('SID list not present')

    def get_queue_name(self, color, direction):
        if(color == self.BLUE):
            return 'blue-ht-' + direction
        else:
            return 'red-ht-' + direction


''' ***************************************** TWAMP RECEIVER '''


class TestPacketReceiver(Thread):
    def __init__(self, interface, sender, reflector,
                 ss_udp_port=1206, refl_udp_port=1205, stop_event=None):
        Thread.__init__(self)
        self.interface = interface
        self.SessionSender = sender
        self.SessionReflector = reflector
        self.ss_udp_port = ss_udp_port
        self.refl_udp_port = refl_udp_port
        self.stop_event = stop_event

    def packetRecvCallback(self, packet):
        # TODO passate dal controller per connessione!!!
        if UDP in packet:
            if packet[UDP].dport == self.refl_udp_port:
                packet[UDP].decode_payload_as(twamp.TWAMPTestQuery)
                # print(packet.show())
                self.SessionReflector.recvTWAMPTestQuery(packet)
            elif packet[UDP].dport == self.ss_udp_port:
                packet[UDP].decode_payload_as(twamp.TWAMPTestResponse)
                # print(packet.show())
                self.SessionSender.recvTWAMPResponse(packet)
            else:
                print(packet.show())

    def run(self):
        stop_filter = None
        if self.stop_event is not None:
            def stop_filter(p): return self.stop_event.is_set()
        print("TestPacketReceiver Start sniffing...")
        sniff(iface=self.interface, filter="ip6", prn=self.packetRecvCallback,
              stop_filter=stop_filter)
        print("TestPacketReceiver Stop sniffing")
        # codice netqueue


''' ***************************************** SENDER '''


class SessionSender(Thread):
    def __init__(self, driver, stop_event=None):
        Thread.__init__(self)
        self.startedMeas = False

        self.ss_udp_port = 1206
        self.refl_udp_port = 1205

        self.monitored_path = {}

        # self.lock = Thread.Lock()

        self.interval = 15
        self.margin = timedelta(milliseconds=3000)
        self.numColor = 2
        self.hwadapter = driver
        self.scheduler = sched.scheduler(time.time, time.sleep)
        # self.startMeas("fcff:3::1/fcff:4::1/fcff:5::1","fcff:4::1/fcff:3::1/fcff:2::1","#test")

        self.stop_event = stop_event

    # def send_meas_data_to_controller(self):     # TODO fix hardcoded params
    #     import random
    #     # Controller IP and port
    #     grpc_ip_controller = '2000::15'
    #     grpc_port_controller = 12345
    #     # Init random seed
    #     random.seed(a=None, version=2)
    #     # Colors
    #     colors = ['red', 'yellow', 'green', 'white', 'purple']
    #     # Loop until startedMeas == True
    #     while True:
    #         # Check if measurement process is started
    #         if not self.startedMeas:
    #             return
    #         # Generate random data
    #         measure_id = random.randint(0, 5)
    #         interval = 10
    #         timestamp = ''
    #         color = random.choice(colors)
    #         sender_tx_counter = random.randint(0, 50)
    #         sender_rx_counter = random.randint(0, 50)
    #         reflector_tx_counter = random.randint(0, 50)
    #         reflector_rx_counter = random.randint(0, 50)
    #         # Create the gRPC request message
    #         request = srv6pmServiceController_pb2.SendMeasurementDataRequest()
    #         data = request.measurement_data.add()
    #         data.measure_id = measure_id
    #         data.interval = interval
    #         data.timestamp = timestamp
    #         data.color = color
    #         data.sender_tx_counter = sender_tx_counter
    #         data.sender_rx_counter = sender_rx_counter
    #         data.reflector_tx_counter = reflector_tx_counter
    #         data.reflector_rx_counter = reflector_rx_counter
    #         channel = grpc.insecure_channel(
    #             'ipv6:[%s]:%s' % grpc_ip_controller, grpc_port_controller)
    #         stub = srv6pmServiceController_pb2_grpc.SRv6PMControllerStub(
    #             channel)
    #         # Send mesaurement data
    #         res = stub.SendMeasurementData(request)
    #         print('Sent data to the controller. Status code: %s' % res.status)
    #         # Wait
    #         time.sleep(self.margin)

    ''' Thread Tasks'''

    def run(self):
        # enter(delay, priority, action, argument=(), kwargs={})
        print("SessionSender start")
        # Starting changeColor task
        ccTime = time.mktime(self.getNexttimeToChangeColor().timetuple())
        self.scheduler.enterabs(ccTime, 1, self.runChangeColor)
        # Starting measure task
        dmTime = time.mktime(self.getNexttimeToMeasure().timetuple())
        self.scheduler.enterabs(dmTime, 1, self.runMeasure)
        self.scheduler.run()
        print("SessionSender stop")

    def runChangeColor(self):
        if self.startedMeas:
            # print(datetime.now(),"SS runChangeColor meas:",self.startedMeas)
            color = self.getColor()
            self.hwadapter.set_color(color)

        if self.stop_event is not None and self.stop_event.is_set():
            print('Terminating runChangeColor')
        else:
            ccTime = time.mktime(self.getNexttimeToChangeColor().timetuple())
            self.scheduler.enterabs(ccTime, 1, self.runChangeColor)

    def runMeasure(self):
        if self.startedMeas:
            # print(datetime.now(),"SS runMeasure meas:",self.startedMeas)
            self.sendTWAMPTestQuery()

        # Schedule next measure
        if self.stop_event is not None and self.stop_event.is_set():
            print('Terminating runMeasure')
        else:
            dmTime = time.mktime(self.getNexttimeToMeasure().timetuple())
            self.scheduler.enterabs(dmTime, 1, self.runMeasure)

    ''' TWAMP methods '''

    def sendTWAMPTestQuery(self):
        try:
            print('sid ist', self.monitored_path)
            # Get the counter for the color of the previuos interval
            senderBlockNumber = self.getPrevColor()
            senderTransmitCounter = self.hwadapter.read_tx_counter(
                senderBlockNumber, self.monitored_path["sidlist"])
            list_rev = list(self.monitored_path["sidlistrev"])
            mod_sidlist = self.set_punt(list_rev)

            ipv6_packet = IPv6()
            ipv6_packet.src = "fcff:1::1"  # TODO me li da il controller?
            ipv6_packet.dst = list_rev[0]  # TODO  me li da il controller?
            # ipv6_packet.dst = 'fcff:3::1'   #TODO  me li da il controller?
            # print("Dest", ipv6_packet.dst)

            srv6_header = IPv6ExtHdrSegmentRouting()
            srv6_header.addresses = mod_sidlist
            # TODO vedere se funziona con NS variabile
            srv6_header.segleft = len(mod_sidlist) - 1
            # TODO vedere se funziona con NS variabile
            srv6_header.lastentry = len(mod_sidlist) - 1

            ipv6_packet_inside = IPv6()
            ipv6_packet_inside.src = "fd00:0:13::1"  # TODO  me li da il controller?
            ipv6_packet_inside.dst = "fd00:0:83::2"  # TODO  me li da il controller?
            ipv6_packet_inside.src = "fcff:1::1"
            ipv6_packet_inside.dst = mod_sidlist[-1]

            udp_packet = UDP()
            udp_packet.dport = self.refl_udp_port
            udp_packet.sport = self.ss_udp_port

            # in band response TODO gestire out band nel controller
            senderControlCode = 1
            senderSeqNum = self.monitored_path["txSequenceNumber"]

            twamp_data = twamp.TWAMPTestQuery(
                SequenceNumber=senderSeqNum,
                TransmitCounter=senderTransmitCounter,
                BlockNumber=senderBlockNumber,
                SenderControlCode=senderControlCode
            )

            pkt = ipv6_packet / srv6_header / ipv6_packet_inside / udp_packet / twamp_data

            print(
                "SS - SEND QUERY SL {sl} -  SN {sn} - TXC {txc} - C {col}".format(
                    sl=mod_sidlist,
                    sn=senderSeqNum,
                    txc=senderTransmitCounter,
                    col=senderBlockNumber))
            send(pkt, count=1, verbose=False)

            # Increase the SN
            self.monitored_path["txSequenceNumber"] += 1
        except Exception as e:
            print(e)

    def recvTWAMPResponse(self, packet):
        # TODO controllare che la sidlist è quella che sto monitorando
        # (levando il punt)
        srh = packet[IPv6ExtHdrSegmentRouting]
        sid_list = srh.addresses
        resp = packet[twamp.TWAMPTestResponse]

        # Read the RX counter FW path
        nopunt_sid_list = self.rem_punt(sid_list)[::-1]  # no punt and reversed
        ssReceiveCounter = self.hwadapter.read_rx_counter(
            resp.BlockNumber, nopunt_sid_list)

        print("SS - RECV QUERY SL {sl} ".format(sl=sid_list))
        print("---          FW: SN {sn} - TX {tx} - RX {rx} - C {col} ".format(
            sn=resp.SenderSequenceNumber,
            tx=resp.SenderCounter,
            rx=resp.ReceiveCounter,
            col=resp.SenderBlockNumber)
        )
        print("---          RV: SN {sn} - TX {tx} - RX {rx} - C {col}".format(
            sn=resp.SequenceNumber,
            tx=resp.TransmitCounter,
            rx=ssReceiveCounter,
            col=resp.BlockNumber)
        )

        self.monitored_path['lastMeas']['sssn'] = resp.SenderSequenceNumber
        self.monitored_path['lastMeas']['ssTXc'] = resp.SenderCounter
        self.monitored_path['lastMeas']['rfRXc'] = resp.ReceiveCounter
        self.monitored_path['lastMeas']['fwColor'] = resp.SenderBlockNumber
        self.monitored_path['lastMeas']['rfsn'] = resp.SequenceNumber
        self.monitored_path['lastMeas']['rfTXc'] = resp.TransmitCounter
        self.monitored_path['lastMeas']['ssRXc'] = ssReceiveCounter
        self.monitored_path['lastMeas']['rvColor'] = resp.BlockNumber

    ''' Interface for the controller'''

    def startMeas(self, meas_id, sidList, revSidList):
        if self.startedMeas:
            return -1  # already started
        print("SESSION SENDER: Start Meas for " + sidList)

        self.monitored_path["meas_id"] = meas_id
        self.monitored_path["sidlistgrpc"] = sidList
        self.monitored_path["sidlist"] = sidList.split("/")
        self.monitored_path["sidlistrev"] = \
            self.monitored_path["sidlist"][::-1]
        self.monitored_path["returnsidlist"] = revSidList.split("/")
        self.monitored_path["returnsidlistrev"] = \
            self.monitored_path["returnsidlist"][::-1]
        self.monitored_path["meas_counter"] = 1  # reset counter
        self.monitored_path["txSequenceNumber"] = 1
        self.monitored_path['lastMeas'] = {}

        self.hwadapter.set_sidlist_out(self.monitored_path["sidlist"])
        self.hwadapter.set_sidlist_in(self.monitored_path["returnsidlist"])
        self.startedMeas = True
        return 1  # mettere in un try e semmai tronare errore

    def stopMeas(self, sidList):
        print("SESSION SENDER: Stop Meas for " + sidList)

        self.startedMeas = False
        self.hwadapter.rem_sidlist_out(self.monitored_path["sidlist"])
        self.hwadapter.rem_sidlist_in(self.monitored_path["returnsidlist"])
        self.monitored_path = {}
        # Clear color options
        # self.interval = None
        # self.margin = None
        # self.numColor = None
        return 1  # mettere in un try e semmai tronare errore

    def getMeas(self, sidList):
        print("SESSION SENDER: Get Meas Data for " + sidList)
        # TODO controllare la sid_list e rilanciate un eccezione
        return self.monitored_path['lastMeas'], self.monitored_path['meas_id']

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
        return (num_interval - 1) % self.numColor

    def set_punt(self, list):
        mod_list = list
        mod_list[0] = mod_list[0][:-3] + "200"
        return mod_list

    def rem_punt(self, list):
        mod_list = list
        mod_list[0] = mod_list[0][:-3] + "100"
        return mod_list


''' ***************************************** REFLECTOR '''


class SessionReflector(Thread):
    def __init__(self, driver, stop_event=None):
        Thread.__init__(self)
        self.name = "SessionReflector"
        self.startedMeas = False
        self.interval = 15
        self.margin = timedelta(milliseconds=3000)
        self.numColor = 2

        self.ss_udp_port = 1206
        self.refl_udp_port = 1205

        self.monitored_path = {}

        self.hwadapter = driver

        # per ora non lo uso è per il cambio di colore
        self.scheduler = sched.scheduler(time.time, time.sleep)

        self.stop_event = stop_event

    def run(self):
        # enter(delay, priority, action, argument=(), kwargs={})
        print("SessionReflector start")
        # Starting changeColor task
        ccTime = time.mktime(self.getNexttimeToChangeColor().timetuple())
        self.scheduler.enterabs(ccTime, 1, self.runChangeColor)
        self.scheduler.run()
        print("SessionReflector stop")

    def runChangeColor(self):
        if self.startedMeas:
            # print(datetime.now(),"RF runChangeColor meas:",self.startedMeas)
            color = self.getColor()
            self.hwadapter.set_color(color)

        if self.stop_event is not None and self.stop_event.is_set():
            print('Terminating runChangeColor')
        else:
            ccTime = time.mktime(self.getNexttimeToChangeColor().timetuple())
            self.scheduler.enterabs(ccTime, 1, self.runChangeColor)

    ''' TWAMP methods '''

    def sendTWAMPTestResponse(self, sid_list, sender_block_color,
                              sender_counter, sender_seq_num):
        # Read the RX counter FW path
        nopunt_sid_list = self.rem_punt(sid_list)[::-1]  # no punt and reversed
        rfReceiveCounter = self.hwadapter.read_rx_counter(
            sender_block_color, nopunt_sid_list)

        # Reverse path
        rfBlockNumber = self.getPrevColor()
        rfTransmitCounter = self.hwadapter.read_tx_counter(
            rfBlockNumber, self.monitored_path["returnsidlist"])

        ipv6_packet = IPv6()
        # ipv6_packet.src = "fcff:5::1" #TODO  me li da il controller?
        # ipv6_packet.dst = "fcff:4::1" #TODO  me li da il controller?
        ipv6_packet.src = "fcff:8::1"
        ipv6_packet.dst = self.monitored_path["returnsidlist"][0]

        mod_sidlist = self.set_punt(
            list(self.monitored_path["returnsidlistrev"]))
        srv6_header = IPv6ExtHdrSegmentRouting()
        srv6_header.addresses = mod_sidlist
        # TODO vedere se funziona con NS variabile
        srv6_header.segleft = len(mod_sidlist) - 1
        # TODO vedere se funziona con NS variabile
        srv6_header.lastentry = len(mod_sidlist) - 1

        ipv6_packet_inside = IPv6()
        # ipv6_packet_inside.src = "fcff:5::1" #TODO  me li da il controller?
        # ipv6_packet_inside.dst = "fcff:2::1" #TODO  me li da il controller?
        ipv6_packet_inside.src = "fcff:8::1"
        ipv6_packet_inside.dst = self.monitored_path["returnsidlist"][-1]

        udp_packet = UDP()
        udp_packet.dport = self.ss_udp_port
        udp_packet.sport = self.refl_udp_port

        # Response sequence number
        rfSequenceNumber = self.monitored_path["revTxSequenceNumber"]

        # Response control code
        rfReceverControlCode = 0

        twamp_data = twamp.TWAMPTestResponse(
            SequenceNumber=rfSequenceNumber,
            TransmitCounter=rfTransmitCounter,
            BlockNumber=rfBlockNumber,
            ReceiveCounter=rfReceiveCounter,
            SenderCounter=sender_counter,
            SenderBlockNumber=sender_block_color,
            SenderSequenceNumber=sender_seq_num,
            ReceverControlCode=rfReceverControlCode
        )

        pkt = ipv6_packet / srv6_header / ipv6_packet_inside / udp_packet / twamp_data

        send(pkt, count=1, verbose=False)
        # Increse the SequenceNumber
        self.monitored_path["revTxSequenceNumber"] += 1

        print(
            "RF - SEND RESP SL {sl} - SN {sn} - TXC {txc} - C {col} - RC {rc}".format(
                sl=mod_sidlist,
                sn=rfSequenceNumber,
                txc=rfTransmitCounter,
                col=rfBlockNumber,
                rc=rfReceiveCounter))

    def recvTWAMPTestQuery(self, packet):
        # TODO controllare che la sidlist è quella che sto monitorando
        # (levando il punt)
        srh = packet[IPv6ExtHdrSegmentRouting]
        sid_list = srh.addresses
        query = packet[twamp.TWAMPTestQuery]
        print("RF - RECV QUERY SL {sl} - SN {sn} - TXC {txc} - C {col}".format(
            sl=sid_list,
            sn=query.SequenceNumber,
            txc=query.TransmitCounter,
            col=query.BlockNumber)
        )

        self.sendTWAMPTestResponse(
            sid_list, query.BlockNumber,
            query.TransmitCounter, query.SequenceNumber
        )

    ''' Interface for the controller'''

    def startMeas(
            self,
            sidList,
            revSidList,
            interval=10,
            margin=5,
            num_color=2):
        if self.startedMeas:
            return -1  # already started
        print("REFLECTOR: Start Meas for " + sidList)

        self.monitored_path["sidlistgrpc"] = sidList
        self.monitored_path["sidlist"] = sidList.split("/")
        self.monitored_path["sidlistrev"] = \
            self.monitored_path["sidlist"][::-1]
        self.monitored_path["returnsidlist"] = revSidList.split("/")
        self.monitored_path["returnsidlistrev"] = \
            self.monitored_path["returnsidlist"][::-1]
        self.monitored_path["revTxSequenceNumber"] = 0
        # Set color options
        self.interval = interval
        self.margin = timedelta(milliseconds=margin)
        self.numColor = num_color
        # pprint.pprint(self.monitored_path)
        self.hwadapter.set_sidlist_in(self.monitored_path["sidlist"])
        self.hwadapter.set_sidlist_out(self.monitored_path["returnsidlist"])
        self.startedMeas = True

    def stopMeas(self, sidList):
        print("REFLECTOR: Stop Meas for " + sidList)

        self.startedMeas = False
        self.hwadapter.rem_sidlist_in(self.monitored_path["sidlist"])
        self.hwadapter.rem_sidlist_out(self.monitored_path["returnsidlist"])
        self.monitored_path = {}
        # Clear color options
        # self.interval = None
        # self.margin = None
        # self.numColor = None
        return 1  # mettere in un try e semmai tornare errore

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
        return (num_interval - 1) % self.numColor

    def set_punt(self, list):
        mod_list = list
        mod_list[0] = mod_list[0][:-3] + "200"
        return mod_list

    def rem_punt(self, list):
        mod_list = list
        mod_list[0] = mod_list[0][:-3] + "100"
        return mod_list
