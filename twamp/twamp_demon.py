#!/usr/bin/python

from concurrent import futures
import grpc
import logging
from threading import Thread
import sched
import time
from scapy.all import *


# FRPC protocol
import srv6pmCommons_pb2_grpc
import srv6pmCommons_pb2
import srv6pmService_pb2_grpc
import srv6pmService_pb2

class TestPacketReceiver(Thread):
    def __init__(self, ctrl , interface):
        Thread.__init__(self) 
        self.interface = interface
        self.TWAMPController = ctrl

    def packetRecvCallback(self, packet):
        print("Packets Recv Callback")
        ip_layer = packet.getlayer(IP)
        print("[!] New Packet: {src} -> {dst}".format(src=ip_layer.src, dst=ip_layer.dst))
        message = ""
        self.TWAMPController.receveQueryResponse(message)

    def run(self):
        print("[*] TestPacketReceiver Start sniffing...")
        sniff(iface=self.interface, filter="udp", prn=self.packetRecvCallback)
        print("[*] TestPacketReceiver Stop sniffing")
        # codice netqueue


class TWAMPController(Thread):
    def __init__(self):
        Thread.__init__(self)
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
        print("TWAMPController start")
        self.scheduler.enter(2, 1, self.doMeasure)
        self.scheduler.run()
        print("TWAMPController stop")

    def receveQueryResponse(self, message):
        print("Received response")


class MeasCtrlReflector(Thread):
    def __init__(self, name):
        Thread.__init__(self)
        self.name = name
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



class TWAMPServicer(srv6pmSender_pb2_grpc.SRv6PMSenderServicer):

    def __init__(self, TWAMPController,MeasCtrlReflector):
        self.port_server = 1234
        self.TWAMPController = TWAMPController
        self.MeasCtrlReflector = MeasCtrlReflector

    def startExperimentSender(self, request, context):
        print("REQ - startExperiment")
        self.TWAMPController.startMeas(request.sdlist)
        res = 1
        return srv6pmSender_pb2.StartExperimentSenderReply(status=res)

    def stopExperimentSender(self, request, context):
        print("REQ - stopExperiment")
        self.TWAMPController.stopMeas(request.sdlist)
        res = 1
        return srv6pmCommons_pb2.StopExperimentReply(status=res)

    def retriveExperimentResultsSender(self, request, context):
        print("REQ - retriveExperimentResults")
        res = self.TWAMPController.getMeas(request.sdlist)
        return srv6pmCommons_pb2.ExperimentDataResponse(status=res)


    def startExperimentReflector(self, request, context):
        print("REQ - startExperiment")
        self.measCtrlRefl.startMeas(request.sdlist)
        return srv6pmReflector_pb2.StartExperimentReflectorReply(status=1)

    def stopExperimentReflector(self, request, context):
        print("REQ - stopExperiment")
        self.measCtrlRefl.stopMeas(request.sdlist)
        return srv6pmCommons_pb2.StopExperimentReply(status=1)

    def retriveExperimentResultsReflector(self, request, context):
        print("REQ - retriveExperimentResults")
        res = self.measCtrlRefl.getMeas(request.sdlist)
        return srv6pmCommons_pb2.ExperimentDataResponse(status=res)


def serve():
    thMeas = TWAMPController()
    thMeas.start()
    thMeasRecv = TestPacketReceiver(thMeas, "ctrl0")
    thMeasRecv.start()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    srv6pmDemon_pb2_grpc.add_SRv6PMDemonServicer_to_server(
        TWAMPServicer(thMeas), server)
    server.add_insecure_port('localhost:50050')
    print("\n-------------- Start Demon --------------\n")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    serve()
