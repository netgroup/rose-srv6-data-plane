#!/usr/bin/python
import srv6pmCommons_pb2_grpc
import srv6pmCommons_pb2
import srv6pmSender_pb2_grpc
import srv6pmSender_pb2
from concurrent import futures
import grpc
import logging
from threading import Thread
import sched
import time
from scapy.all import *



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


class SenderServicer(srv6pmSender_pb2_grpc.SRv6PMSenderServicer):

    def __init__(self, TWAMPController):
        self.port_server = 1234
        self.TWAMPController = TWAMPController

    def startExperiment(self, request, context):
        print("REQ - startExperiment")
        self.TWAMPController.startMeas(request.sdlist)
        res = 1
        return srv6pmSender_pb2.StartExperimentSenderReply(status=res)

    def stopExperiment(self, request, context):
        print("REQ - stopExperiment")
        self.TWAMPController.stopMeas(request.sdlist)
        res = 1
        return srv6pmCommons_pb2.StopExperimentReply(status=res)

    def retriveExperimentResults(self, request, context):
        print("REQ - retriveExperimentResults")
        res = self.TWAMPController.getMeas(request.sdlist)
        return srv6pmCommons_pb2.ExperimentDataResponse(status=res)


def serve():
    thMeas = TWAMPController()
    thMeas.start()
    thMeasRecv = TestPacketReceiver(thMeas, "ctrl0")
    thMeasRecv.start()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    srv6pmSender_pb2_grpc.add_SRv6PMSenderServicer_to_server(
        SenderServicer(thMeas), server)
    server.add_insecure_port('localhost:50052')
    print("\n-------------- Server Sarted --------------\n")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    serve()