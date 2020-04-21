#!/usr/bin/python

from concurrent import futures
import grpc
import logging
from threading import Thread
import sched
import time
from scapy.all import *
from scapy.layers.inet import IP,UDP


# FRPC protocol
import srv6pmCommons_pb2_grpc
import srv6pmCommons_pb2
import srv6pmService_pb2_grpc
import srv6pmService_pb2

class TestPacketReceiver(Thread):
    def __init__(self, ctrl , interface):
        Thread.__init__(self) 
        self.interface = interface
        self.SessionSender = ctrl

    def packetRecvCallback(self, packet):
        print("Packets Recv Callback")
        packet[UDP].decode_payload_as(Raw)
        print(packet.show())
		
        ip_layer = packet.getlayer(IP)
        print("[!] New Packet: {src} -> {dst}".format(src=ip_layer.src, dst=ip_layer.dst))
        message = ""
        raw_layer = packet.getlayer(Raw)
        print("[!] TWAMP Payload: {payload} ".format(payload=raw_layer.load))
        self.SessionSender.receveQueryResponse(message)

    def run(self):
        print("TestPacketReceiver Start sniffing...")
        sniff(iface=self.interface, filter="udp and port 50050", prn=self.packetRecvCallback)
        print("TestPacketReceiver Stop sniffing")
        # codice netqueue


class SessionSender(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.SessionSenderRecv = TestPacketReceiver(self,"ctrl0") # packet recever
        self.startedMeas = False
        self.counter = {}
        # self.lock = Thread.Lock()
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def startMeas(self, sidList):
        print("CTRL: Start Meas for "+sidList)
        self.counter[sidList] = 0
        self.startedMeas = True

    def stopMeas(self, sidList):
        print("CTRL: Stop Meas for "+sidList)
        self.startedMeas = False

    def doMeasure(self):
        if self.startedMeas:
            print("CTRL: Loss Probe / Color")
            for sl in self.counter:
                self.counter[sl] += 1
        self.scheduler.enter(2, 1, self.doMeasure)

    def getMeas(self, sidList):
        print("CTRL: Get Mead Data for "+sidList)
        return self.counter[sidList]

    def run(self):
        print("Starting the Packet Receiver")
        self.SessionSenderRecv.start()

        print("SessionSender start")
        self.scheduler.enter(2, 1, self.doMeasure)
        self.scheduler.run()
        print("SessionSender stop")

    def receveQueryResponse(self, message):
        print("Received response")


class SessionReflector(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.name = "SessionReflector"
        self.startedMeas = False
        self.counter = {}
        # self.lock = Thread.Lock()
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def startMeas(self, sidList):
        print("CTRL REFL: Start Meas for "+sidList)
        self.counter[sidList] = 0
        self.startedMeas = True

    def stopMeas(self, sidList):
        print("CTRL REFL: Stop Meas for "+sidList)
        self.startedMeas = False

    def doMeasure(self):
        # print("Do Meas ST:"+str(self.startedMeas))
        if self.startedMeas:
            print("CTRL REFL: Loss Probe / Color")
            for sl in self.counter:
                self.counter[sl] += 10
        self.scheduler.enter(2, 1, self.doMeasure)

    def getMeas(self, sidList):
        print("CTRL REFL: Get Mead Data for "+sidList)
        return self.counter[sidList]

    def run(self):
        print("Thread '" + self.name + "' start")
        self.scheduler.enter(2, 1, self.doMeasure)
        self.scheduler.run()
        print("Thread '" + self.name + "' stop")

    def receveQuery(self, message):
        print("Received Query")



class TWAMPController(srv6pmService_pb2_grpc.SRv6PMServicer):
    def __init__(self, SessionSender,SessionReflector):
        self.port_server = 20000
        self.SessionSender = SessionSender
        self.SessionReflector = SessionReflector

    def startExperimentSender(self, request, context):
        print("REQ - startExperiment")
        self.SessionSender.startMeas(request.sdlist)
        res = 1
        return srv6pmService_pb2.StartExperimentSenderReply(status=res)

    def stopExperimentSender(self, request, context):
        print("REQ - stopExperiment")
        self.SessionSender.stopMeas(request.sdlist)
        res = 1
        return srv6pmCommons_pb2.StopExperimentReply(status=res)

    def retriveExperimentResultsSender(self, request, context):
        print("REQ - retriveExperimentResults")
        res = self.SessionSender.getMeas(request.sdlist)
        return srv6pmCommons_pb2.ExperimentDataResponse(status=res)


    def startExperimentReflector(self, request, context):
        print("REQ - startExperiment")
        self.measCtrlRefl.startMeas(request.sdlist)
        return srv6pmService_pb2.StartExperimentReflectorReply(status=1)

    def stopExperimentReflector(self, request, context):
        print("REQ - stopExperiment")
        self.measCtrlRefl.stopMeas(request.sdlist)
        return srv6pmCommons_pb2.StopExperimentReply(status=1)

    def retriveExperimentResultsReflector(self, request, context):
        print("REQ - retriveExperimentResults")
        res = self.measCtrlRefl.getMeas(request.sdlist)
        return srv6pmCommons_pb2.ExperimentDataResponse(status=res)


def serve(ipaddr,gprcPort):
    sessionsender = SessionSender()
    sessionsender.start()
    sessionreflector = SessionReflector()
    sessionreflector.start()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    srv6pmService_pb2_grpc.add_SRv6PMServicer_to_server(TWAMPController(sessionsender,sessionreflector), server)
    server.add_insecure_port("{ip}:{port}".format(ip=ipaddr,port=gprcPort))
    print("\n-------------- Start Demon --------------\n")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    ipaddr =  sys.argv[1]
    gprcPort =  sys.argv[2]

    logging.basicConfig()
    serve(ipaddr,gprcPort)
