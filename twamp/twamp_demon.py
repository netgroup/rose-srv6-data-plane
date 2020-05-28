#!/usr/bin/python

import os

# Activate virtual environment if a venv path has been specified in .venv
# This must be executed only if this file has been executed as a
# script (instead of a module)
if __name__ == '__main__':
    # Check if .venv file exists
    if os.path.exists('.venv'):
        with open('.venv', 'r') as venv_file:
            # Get virtualenv path from .venv file
            # and remove trailing newline chars
            venv_path = venv_file.read().rstrip()
        # Get path of the activation script
        venv_path = os.path.join(venv_path, 'bin/activate_this.py')
        if not os.path.exists(venv_path):
            print('Virtual environment path specified in .venv '
                  'points to an invalid path\n')
            exit(-2)
        with open(venv_path) as f:
            # Read the activation script
            code = compile(f.read(), venv_path, 'exec')
            # Execute the activation script to activate the venv
            exec(code, {'__file__': venv_path})

from concurrent import futures
from dotenv import load_dotenv
import sys
import grpc
import logging
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
import twamp

# Load environment variables from .env file
load_dotenv()

# Folder containing this script
BASE_PATH = os.path.dirname(os.path.realpath(__file__))

# Folder containing the SRV6_PFPLM files
SRV6_PFPLM_PATH = '/home/rose/workspace/srv6_pfplm'

# Environment variables have priority over hardcoded paths
# If an environment variable is set, we must use it instead of
# the hardcoded constant
if os.getenv('SRV6_PFPLM_PATH') is not None:
    # Check if the SRV6_PFPLM_PATH variable is set
    if os.getenv('SRV6_PFPLM_PATH') == '':
        print('Error : Set SRV6_PFPLM_PATH variable in .env\n')
        sys.exit(-2)
    # Check if the SRV6_PFPLM_PATH variable points to an existing folder
    if not os.path.exists(os.getenv('SRV6_PFPLM_PATH')):
        print('Error : SRV6_PFPLM_PATH variable in '
              '.env points to a non existing folder')
        sys.exit(-2)
    # SRV6_PFPLM_PATH in .env is correct. We use it.
    SRV6_PFPLM_PATH = os.getenv('SRV6_PFPLM_PATH')
else:
    # SRV6_PFPLM_PATH in .env is not set, we use the hardcoded path
    #
    # Check if the SRV6_PFPLM_PATH variable is set
    if SRV6_PFPLM_PATH == '':
        print('Error : Set SRV6_PFPLM_PATH variable in .env or %s' %
              sys.argv[0])
        sys.exit(-2)
    # Check if the SRV6_PFPLM_PATH variable points to an existing folder
    if not os.path.exists(SRV6_PFPLM_PATH):
        print('Error : SRV6_PFPLM_PATH variable in '
              '%s points to a non existing folder' % sys.argv[0])
        print('Error : Set SRV6_PFPLM_PATH variable in .env or %s\n' %
              sys.argv[0])
        sys.exit(-2)

# SRv6 PFPLM dependencies
sys.path.append(SRV6_PFPLM_PATH)

from xdp_srv6_pfplm_helper_user import EbpfException, EbpfPFPLM


''' ***************************************** DRIVER EBPF '''


class EbpfInterf():
    def __init__(self):
        self.inDriver = EbpfPFPLM()
        self.outDriver = EbpfPFPLM()
        self.outInterface = None
        self.inInterface = None
        self.BLUE = 1
        self.RED = 0
        self.mark = [1, 2]

    def start(self, outInterface, inInterface):
        try:
            self.inInterface = inInterface
            self.outInterface = outInterface

            self.inDriver.pfplm_load(
                self.inInterface, self.inDriver.lib.XDP_PROG_DIR_INGRESS,
                self.inDriver.lib.F_VERBOSE | self.inDriver.lib.F_FORCE)

            self.outDriver.pfplm_load(
                self.outInterface, self.outDriver.lib.XDP_PROG_DIR_EGRESS,
                self.outDriver.lib.F_VERBOSE | self.outDriver.lib.F_FORCE)
            self.outDriver.pfplm_change_active_color(
                self.outInterface, self.mark[self.BLUE])
        except EbpfException as e:
            e.print_exception()

    def stop(self):
        try:
            self.inDriver.pfplm_unload(
                self.inInterface, self.inDriver.lib.XDP_PROG_DIR_INGRESS,
                self.inDriver.lib.F_VERBOSE | self.inDriver.lib.F_FORCE)

            self.outDriver.pfplm_unload(
                self.outInterface, self.outDriver.lib.XDP_PROG_DIR_EGRESS,
                self.outDriver.lib.F_VERBOSE | self.outDriver.lib.F_FORCE)
        except EbpfException as e:
            e.print_exception()

    def sid_list_converter(self, sid_list):
        return ",".join(sid_list)

    def set_sidlist_out(self, sid_list):
        ebpf_sid_list = self.sid_list_converter(sid_list)
        print("EBPF INS OUT sidlist", ebpf_sid_list)
        try:
            self.outDriver.pfplm_add_flow(
                self.outInterface, ebpf_sid_list)  # da testare
        except EbpfException as e:
            e.print_exception()

    def set_sidlist_in(self, sid_list):
        ebpf_sid_list = self.sid_list_converter(sid_list)
        print("EBPF INS IN sidlist", ebpf_sid_list)
        try:
            self.inDriver.pfplm_add_flow(
                self.inInterface, ebpf_sid_list)  # da testare
        except EbpfException as e:
            e.print_exception()

    def rem_sidlist_out(self, sid_list):
        ebpf_sid_list = self.sid_list_converter(sid_list)
        print("EBPF REM sidlist", ebpf_sid_list)
        try:
            self.outDriver.pfplm_del_flow(
                self.outInterface, ebpf_sid_list)  # da testare
        except EbpfException as e:
            e.print_exception()

    def rem_sidlist_in(self, sid_list):
        ebpf_sid_list = self.sid_list_converter(sid_list)
        print("EBPF REM sidlist", ebpf_sid_list)
        try:
            self.inDriver.pfplm_del_flow(
                self.inInterface, ebpf_sid_list)  # da testare
        except EbpfException as e:
            e.print_exception()

    def set_color(self, color):
        if(color == self.BLUE):
            self.outDriver.pfplm_change_active_color(
                self.outInterface, self.mark[self.BLUE])
        else:
            self.outDriver.pfplm_change_active_color(
                self.outInterface, self.mark[self.RED])

    def read_tx_counter(self, color, sid_list):
        ebpf_sid_list = self.sid_list_converter(sid_list)
        return self.outDriver.pfplm_get_flow_stats(
            self.outInterface, ebpf_sid_list, self.mark[color])

    def read_rx_counter(self, color, sid_list):
        ebpf_sid_list = self.sid_list_converter(sid_list)
        return self.inDriver.pfplm_get_flow_stats(
            self.inInterface, ebpf_sid_list, self.mark[color])


''' ***************************************** DRIVER IPSET '''


class IpSetInterf():
    def __init__(self):
        self.interface = ""
        self.BLUE = 1
        self.RED = 0
        self.state = self.BLUE  # base conf use blue queue

    def start(self, outInterface, inInterface):
        pass

    def stop(self):
        pass

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
                    return int(int(cnt)/2)

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
            return 'blue-ht-'+direction
        else:
            return 'red-ht-'+direction


''' ***************************************** TWAMP RECEIVER '''


class TestPacketReceiver(Thread):
    def __init__(self, interface, sender,
                 reflector, ss_udp_port=1206, refl_udp_port=1205):
        Thread.__init__(self)
        self.interface = interface
        self.SessionSender = sender
        self.SessionReflector = reflector
        self.ss_udp_port = ss_udp_port
        self.refl_udp_port = refl_udp_port

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
        print("TestPacketReceiver Start sniffing...")
        sniff(iface=self.interface, filter="ip6", prn=self.packetRecvCallback)
        print("TestPacketReceiver Stop sniffing")
        # codice netqueue


''' ***************************************** SENDER '''


class SessionSender(Thread):
    def __init__(self, driver):
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

        ccTime = time.mktime(self.getNexttimeToChangeColor().timetuple())
        self.scheduler.enterabs(ccTime, 1, self.runChangeColor)

    def runMeasure(self):
        if self.startedMeas:
            # print(datetime.now(),"SS runMeasure meas:",self.startedMeas)
            self.sendTWAMPTestQuery()

        # Schedule next measure
        dmTime = time.mktime(self.getNexttimeToMeasure().timetuple())
        self.scheduler.enterabs(dmTime, 1, self.runMeasure)

    ''' TWAMP methods '''

    def sendTWAMPTestQuery(self):
        try:
            # Get the counter for the color of the previuos interval
            senderBlockNumber = self.getPrevColor()
            senderTransmitCounter = self.hwadapter.read_tx_counter(
                senderBlockNumber, self.monitored_path["sidlist"])

            ipv6_packet = IPv6()
            # ipv6_packet.src = "fcff:1::1" #TODO me li da il controller?
            # ipv6_packet.dst = "fcff:4::1" #TODO  me li da il controller?
            ipv6_packet.src = "fcf0:0:1:2::1"
            ipv6_packet.dst = self.monitored_path["sidlist"][0]

            mod_sidlist = self.set_punt(
                list(self.monitored_path["sidlistrev"]))

            srv6_header = IPv6ExtHdrSegmentRouting()
            srv6_header.addresses = mod_sidlist
            # TODO vedere se funziona con NS variabile
            srv6_header.segleft = len(mod_sidlist)-1
            # TODO vedere se funziona con NS variabile
            srv6_header.lastentry = len(mod_sidlist)-1

            ipv6_packet_inside = IPv6()
            # ipv6_packet_inside.src = "fd00:0:13::1" #TODO  me li da il
            # controller?
            # ipv6_packet_inside.dst = "fd00:0:83::2" #TODO  me li da il
            # controller?
            ipv6_packet_inside.src = "fcff:1::1"
            ipv6_packet_inside.dst = self.monitored_path["sidlist"][-1]

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

            print("SS - SEND QUERY SL {sl} -  SN {sn} - TXC {txc} - C {col}".format(
                sl=mod_sidlist,
                sn=senderSeqNum,
                txc=senderTransmitCounter,
                col=senderBlockNumber)
            )
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

    def startMeas(self, meas_id, sidList, revSidList, inInterface, outInterface):
        if self.startedMeas:
            return -1  # already started
        print("SESSION SENDER: Start Meas for "+sidList)

        self.hwadapter.start(outInterface, inInterface)

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
        print("SESSION SENDER: Stop Meas for "+sidList)

        self.hwadapter.stop()

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
        print("SESSION SENDER: Get Meas Data for "+sidList)
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
        return (num_interval-1) % self.numColor

    def set_punt(self, list):
        mod_list = list
        mod_list[0] = mod_list[0][:-3]+"200"
        return mod_list

    def rem_punt(self, list):
        mod_list = list
        mod_list[0] = mod_list[0][:-3]+"100"
        return mod_list


''' ***************************************** REFLECTOR '''


class SessionReflector(Thread):
    def __init__(self, driver):
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
        srv6_header.segleft = len(mod_sidlist)-1
        # TODO vedere se funziona con NS variabile
        srv6_header.lastentry = len(mod_sidlist)-1

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

        print("RF - SEND RESP SL {sl} - SN {sn} - TXC {txc} - C {col} - RC {rc}".format(
            sl=mod_sidlist,
            sn=rfSequenceNumber,
            txc=rfTransmitCounter,
            col=rfBlockNumber,
            rc=rfReceiveCounter)
        )

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

    def startMeas(self, sidList, revSidList, inInterface, outInterface):
        if self.startedMeas:
            return -1  # already started
        print("REFLECTOR: Start Meas for "+sidList)

        self.hwadapter.start(outInterface, inInterface)

        self.monitored_path["sidlistgrpc"] = sidList
        self.monitored_path["sidlist"] = sidList.split("/")
        self.monitored_path["sidlistrev"] = \
            self.monitored_path["sidlist"][::-1]
        self.monitored_path["returnsidlist"] = revSidList.split("/")
        self.monitored_path["returnsidlistrev"] = \
            self.monitored_path["returnsidlist"][::-1]
        self.monitored_path["revTxSequenceNumber"] = 0
        # pprint.pprint(self.monitored_path)
        self.hwadapter.set_sidlist_in(self.monitored_path["sidlist"])
        self.hwadapter.set_sidlist_out(self.monitored_path["returnsidlist"])
        self.startedMeas = True

    def stopMeas(self, sidList):
        print("REFLECTOR: Stop Meas for "+sidList)

        self.hwadapter.stop()

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
        return (num_interval-1) % self.numColor

    def set_punt(self, list):
        mod_list = list
        mod_list[0] = mod_list[0][:-3]+"200"
        return mod_list

    def rem_punt(self, list):
        mod_list = list
        mod_list[0] = mod_list[0][:-3]+"100"
        return mod_list
